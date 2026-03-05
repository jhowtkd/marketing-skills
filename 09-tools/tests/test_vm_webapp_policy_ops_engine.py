"""Testes unitários de fronteira para PolicyOpsEngine.

v47: Batch 2 - Testes de confiança, sample size, dados faltantes e modo MANUAL.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from vm_webapp.onboarding_rollout_policy import (
    BenchmarkMetrics,
    RolloutMode,
    RolloutPolicy,
)
from vm_webapp.policy_ops_engine import (
    PolicyOpsEngine,
    PolicyRecommendation,
    RecommendationAction,
    RecommendationStatus,
    EvaluationResult,
    get_pending_recommendations,
    update_recommendation_status,
)


class TestPolicyOpsEngineConfidenceBoundary:
    """Testes de fronteira para confidence scores."""

    def test_confidence_zero_all_gates_failed(self):
        """Testar confidence baixo (sample size zero, todas gates falharam)."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        # Métricas com sample_size zero e gates falhados
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=0,
        )
        variant = BenchmarkMetrics(
            ttfv=50.0,  # Muito pior
            completion_rate=0.5,  # Muito pior
            abandonment_rate=0.5,  # Muito pior
            score=0.5,  # Muito pior
            sample_size=0,  # Sample size zero
        )
        
        policy = RolloutPolicy(
            experiment_id="test_zero_confidence",
            rollout_mode=RolloutMode.AUTO,
        )
        
        # Todas as gates devem falhar
        gates_passed = []
        gates_failed = ["gain_gate", "stability_gate", "risk_gate", "abandonment_gate", "regression_gate"]
        
        confidence = engine._calculate_confidence(
            control, variant, gates_passed, gates_failed
        )
        
        # Confidence deve ser baixo (sample=0, gates=0, stability=0.8)
        # Expected: 0.4*0 + 0.3*0.8 + 0.3*0 = 0.24
        assert confidence < 0.3
        assert confidence >= 0.0

    def test_confidence_one_all_gates_passed(self):
        """Testar confidence=1.0 (sample size alto, todas gates passaram)."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        # Métricas com sample_size alto e gates passados
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=1000,
        )
        variant = BenchmarkMetrics(
            ttfv=20.0,  # Melhor
            completion_rate=0.90,  # Melhor
            abandonment_rate=0.10,  # Melhor
            score=1.1,  # Melhor
            sample_size=1000,  # Sample size alto
        )
        
        policy = RolloutPolicy(
            experiment_id="test_full_confidence",
            rollout_mode=RolloutMode.AUTO,
        )
        
        # Todas as gates devem passar
        gates_passed = ["gain_gate", "stability_gate", "risk_gate", "abandonment_gate", "regression_gate"]
        gates_failed = []
        
        confidence = engine._calculate_confidence(
            control, variant, gates_passed, gates_failed
        )
        
        # Confidence deve ser alto (> 0.8)
        assert confidence > 0.8
        assert confidence <= 1.0


class TestPolicyOpsEngineSampleSizeBoundary:
    """Testes de fronteira para sample size threshold."""

    def test_sample_size_at_minimum_threshold(self):
        """Testar sample size exatamente no threshold mínimo (30)."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=100,
        )
        # Sample size exatamente no threshold
        variant = BenchmarkMetrics(
            ttfv=22.0,
            completion_rate=0.88,
            abandonment_rate=0.12,
            score=1.02,
            sample_size=30,  # Exatamente no mínimo
        )
        
        policy = RolloutPolicy(
            experiment_id="test_min_sample",
            rollout_mode=RolloutMode.AUTO,
        )
        
        gates_passed = ["stability_gate"]  # Passa no mínimo
        gates_failed = []
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=control,
            variant_metrics=variant,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )
        
        # Não deve ser HOLD por sample size
        assert "sample size" not in rationale.lower() or "insufficient" not in rationale.lower()

    def test_sample_size_below_minimum_threshold(self):
        """Testar sample size abaixo do threshold mínimo (29)."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=100,
        )
        # Sample size abaixo do threshold
        variant = BenchmarkMetrics(
            ttfv=22.0,
            completion_rate=0.88,
            abandonment_rate=0.12,
            score=1.02,
            sample_size=29,  # Abaixo do mínimo
        )
        
        policy = RolloutPolicy(
            experiment_id="test_below_sample",
            rollout_mode=RolloutMode.AUTO,
        )
        
        gates_passed = []
        gates_failed = ["stability_gate"]
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=control,
            variant_metrics=variant,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )
        
        # Deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert "sample size" in rationale.lower() or "insufficient" in rationale.lower()


class TestPolicyOpsEngineMissingData:
    """Testes para dados faltantes."""

    def test_metrics_none_control_missing(self):
        """Testar quando métricas de controle são None."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_missing_control",
            rollout_mode=RolloutMode.AUTO,
        )
        
        variant = BenchmarkMetrics(
            ttfv=22.0,
            completion_rate=0.88,
            abandonment_rate=0.12,
            score=1.02,
            sample_size=50,
        )
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=None,
            variant_metrics=variant,
            gates_passed=[],
            gates_failed=["metrics_unavailable"],
        )
        
        # Deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert confidence == 0.0

    def test_metrics_none_variant_missing(self):
        """Testar quando métricas de variante são None."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_missing_variant",
            rollout_mode=RolloutMode.AUTO,
        )
        
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=100,
        )
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=control,
            variant_metrics=None,
            gates_passed=[],
            gates_failed=["metrics_unavailable"],
        )
        
        # Deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert confidence == 0.0

    def test_both_metrics_none(self):
        """Testar quando ambas as métricas são None."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_both_missing",
            rollout_mode=RolloutMode.AUTO,
        )
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=None,
            variant_metrics=None,
            gates_passed=[],
            gates_failed=["metrics_unavailable"],
        )
        
        # Deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert confidence == 0.0
        assert "insufficient metrics" in rationale.lower() or "waiting for more samples" in rationale.lower()


class TestPolicyOpsEngineManualMode:
    """Testes para modo MANUAL."""

    def test_manual_mode_always_returns_hold(self):
        """Testar que modo MANUAL sempre retorna HOLD."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=100,
        )
        variant = BenchmarkMetrics(
            ttfv=15.0,  # Muito melhor
            completion_rate=0.95,  # Muito melhor
            abandonment_rate=0.05,  # Muito melhor
            score=1.2,  # Muito melhor
            sample_size=100,
        )
        
        policy = RolloutPolicy(
            experiment_id="test_manual_mode",
            rollout_mode=RolloutMode.MANUAL,
        )
        
        # Todas as gates passam
        gates_passed = ["gain_gate", "stability_gate", "risk_gate", "abandonment_gate", "regression_gate"]
        gates_failed = []
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=control,
            variant_metrics=variant,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )
        
        # Mesmo com todas as gates passando, deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert "manual" in rationale.lower()

    def test_manual_mode_with_metrics_none(self):
        """Testar modo MANUAL mesmo quando métricas são None."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_manual_none",
            rollout_mode=RolloutMode.MANUAL,
        )
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=None,
            variant_metrics=None,
            gates_passed=[],
            gates_failed=[],
        )
        
        # Deve retornar HOLD
        assert action == RecommendationAction.HOLD
        assert "manual" in rationale.lower()


class TestPolicyOpsEngineSupervisedMode:
    """Testes para modo SUPERVISED - nunca promove automaticamente."""

    def test_supervised_mode_never_auto_promote(self):
        """Testar que SUPERVISED nunca retorna PROMOTE automaticamente."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        control = BenchmarkMetrics(
            ttfv=25.0,
            completion_rate=0.85,
            abandonment_rate=0.15,
            score=1.0,
            sample_size=100,
        )
        variant = BenchmarkMetrics(
            ttfv=15.0,  # Muito melhor
            completion_rate=0.95,  # Muito melhor
            abandonment_rate=0.05,  # Muito melhor
            score=1.2,  # Muito melhor
            sample_size=100,
        )
        
        policy = RolloutPolicy(
            experiment_id="test_supervised_mode",
            rollout_mode=RolloutMode.SUPERVISED,
        )
        
        # Todas as gates passam
        gates_passed = ["gain_gate", "stability_gate", "risk_gate", "abandonment_gate", "regression_gate"]
        gates_failed = []
        
        action, confidence, rationale = engine._recommend_action(
            policy=policy,
            control_metrics=control,
            variant_metrics=variant,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )
        
        # Não deve retornar PROMOTE mesmo com todas as gates passando
        assert action != RecommendationAction.PROMOTE
        assert action == RecommendationAction.HOLD
        assert "supervised" in rationale.lower()
        assert "manual approval" in rationale.lower()


class TestPolicyOpsEngineFailSafeMetrics:
    """Testes para fail-safe de métricas em modo real."""

    def test_fetch_metrics_raises_when_use_synthetic_false(self):
        """Testar que _fetch_metrics lança exceção quando use_synthetic=False."""
        engine = PolicyOpsEngine(use_synthetic=False)
        
        # Deve lançar exceção quando métricas não estão disponíveis
        with pytest.raises(RuntimeError) as exc_info:
            engine._fetch_metrics("test_experiment")
        
        assert "metrics not available" in str(exc_info.value).lower() or "synthetic" in str(exc_info.value).lower()

    def test_fetch_metrics_returns_synthetic_when_enabled(self):
        """Testar que _fetch_metrics retorna dados sintéticos quando use_synthetic=True."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        # Não deve lançar exceção
        control, variant = engine._fetch_metrics("test_experiment")
        
        assert control is not None
        assert variant is not None
        assert control.sample_size > 0
        assert variant.sample_size > 0


class TestPolicyOpsEngineIdempotentPersistence:
    """Testes para persistência idempotente com escrita atômica."""

    def test_save_recommendation_is_idempotent(self, tmp_path):
        """Testar que salvar recomendação duas vezes não cria duplicata."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        # Mock do diretório de configuração
        config_dir = tmp_path / "policy_ops"
        config_dir.mkdir(parents=True)
        
        with patch.object(engine, '_get_config_dir', return_value=config_dir):
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            rec1 = PolicyRecommendation(
                experiment_id="test_idempotent",
                action=RecommendationAction.HOLD,
                confidence=0.5,
                rationale="Test rationale",
                status=RecommendationStatus.PENDING,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
            
            # Salvar primeira vez
            engine._save_recommendation(rec1)
            
            # Salvar segunda vez (mesmo experiment_id, mesmo dia)
            rec2 = PolicyRecommendation(
                experiment_id="test_idempotent",
                action=RecommendationAction.HOLD,
                confidence=0.6,  # Diferente confiança
                rationale="Updated rationale",
                status=RecommendationStatus.PENDING,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
            engine._save_recommendation(rec2)
            
            # Verificar que só existe um arquivo
            files = list(config_dir.glob("*_recommendation.json"))
            assert len(files) == 1
            
            # Verificar que o conteúdo foi atualizado
            with open(files[0]) as f:
                data = json.load(f)
            
            # Deve ter o conteúdo mais recente
            assert data["confidence"] == 0.6
            assert data["rationale"] == "Updated rationale"

    def test_atomic_write_uses_tempfile(self, tmp_path):
        """Testar que escrita usa tempfile + rename para atomicidade."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        config_dir = tmp_path / "policy_ops"
        config_dir.mkdir(parents=True)
        
        with patch.object(engine, '_get_config_dir', return_value=config_dir):
            rec = PolicyRecommendation(
                experiment_id="test_atomic",
                action=RecommendationAction.HOLD,
                confidence=0.5,
                rationale="Test",
                status=RecommendationStatus.PENDING,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
            
            # Verificar que mkstemp é usado (implementação atual usa mkstemp + rename)
            with patch('tempfile.mkstemp') as mock_mkstemp:
                mock_fd = 123
                mock_temp_path = str(tmp_path / ".tmp_test_atomic_xyz.json")
                mock_mkstemp.return_value = (mock_fd, mock_temp_path)
                
                with patch('os.fdopen') as mock_fdopen:
                    mock_file = mock_fdopen.return_value.__enter__.return_value
                    
                    with patch('os.rename') as mock_rename:
                        engine._save_recommendation(rec)
                        
                        # Deve ter chamado mkstemp para criar tempfile
                        mock_mkstemp.assert_called_once()
                        # Deve ter chamado rename para atomic move
                        mock_rename.assert_called_once()


class TestPolicyOpsEngineIntegration:
    """Testes de integração."""

    def test_evaluate_single_policy_creates_recommendation(self, tmp_path):
        """Testar que avaliação cria uma recomendação completa."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_integration",
            rollout_mode=RolloutMode.AUTO,
        )
        
        # Mock do diretório de configuração
        config_dir = tmp_path / "policy_ops"
        config_dir.mkdir(parents=True)
        
        with patch.object(engine, '_get_config_dir', return_value=config_dir):
            result = engine._evaluate_single_policy(policy, dry_run=False)
            
            assert isinstance(result, EvaluationResult)
            assert result.experiment_id == "test_integration"
            assert isinstance(result.recommendation, PolicyRecommendation)
            assert result.recommendation.status == RecommendationStatus.PENDING
            
            # Verificar que foi salvo
            files = list(config_dir.glob("*_recommendation.json"))
            assert len(files) == 1

    def test_dry_run_does_not_persist(self, tmp_path):
        """Testar que dry_run não persiste recomendação."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        policy = RolloutPolicy(
            experiment_id="test_dry_run",
            rollout_mode=RolloutMode.AUTO,
        )
        
        config_dir = tmp_path / "policy_ops"
        config_dir.mkdir(parents=True)
        
        with patch.object(engine, '_get_config_dir', return_value=config_dir):
            result = engine._evaluate_single_policy(policy, dry_run=True)
            
            assert isinstance(result, EvaluationResult)
            
            # Verificar que NÃO foi salvo
            files = list(config_dir.glob("*_recommendation.json"))
            assert len(files) == 0


class TestPolicyOpsEngineConfig:
    """Testes para configuração do engine."""

    def test_default_config_values(self):
        """Testar valores padrão de configuração."""
        engine = PolicyOpsEngine(use_synthetic=True)
        
        assert engine._config["min_confidence_for_auto"] == 0.8
        assert engine._config["min_sample_size"] == 30
        assert engine._config["default_expiry_hours"] == 24
        assert "confidence_weights" in engine._config

    def test_load_config_from_file(self, tmp_path):
        """Testar carregamento de configuração de arquivo."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "min_confidence_for_auto": 0.9,
            "min_sample_size": 50,
        }))
        
        engine = PolicyOpsEngine(config_path=config_file, use_synthetic=True)
        
        assert engine._config["min_confidence_for_auto"] == 0.9
        assert engine._config["min_sample_size"] == 50
        # Valores padrão ainda devem existir
        assert engine._config["default_expiry_hours"] == 24
