#!/usr/bin/env python3
"""
Vibe Marketing - Research Tools
Ferramentas gratuitas de pesquisa de mercado
"""

import requests
import json
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import re


class MarketResearch:
    """Classe principal para pesquisa de mercado"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_duckduckgo(self, query, max_results=10):
        """
        Busca no DuckDuckGo (gratuito)
        
        Args:
            query: Termo de busca
            max_results: Número máximo de resultados
            
        Returns:
            Lista de resultados
        """
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result', limit=max_results):
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True)
                    })
            
            return results
            
        except Exception as e:
            print(f"Erro na busca DuckDuckGo: {e}")
            return []
    
    def scrape_website(self, url):
        """
        Extrai informações de um website
        
        Args:
            url: URL do site
            
        Returns:
            Dicionário com informações extraídas
        """
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair título
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            
            # Extrair meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # Extrair headings
            h1_tags = [h.get_text(strip=True) for h in soup.find_all('h1')]
            h2_tags = [h.get_text(strip=True) for h in soup.find_all('h2')]
            
            # Extrair preços (padrão comum)
            price_pattern = r'R\$[\s]?[\d.]+[,\d]+|[\d.]+[,\d]+'
            prices = re.findall(price_pattern, response.text)
            
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'h1_tags': h1_tags,
                'h2_tags': h2_tags,
                'prices_found': list(set(prices))[:10],  # Primeiros 10 únicos
                'status_code': response.status_code
            }
            
        except Exception as e:
            print(f"Erro ao fazer scraping de {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def analyze_competitor(self, url):
        """
        Análise completa de um concorrente
        
        Args:
            url: URL do site do concorrente
            
        Returns:
            Análise estruturada
        """
        data = self.scrape_website(url)
        
        analysis = {
            'url': url,
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'main_headlines': data.get('h1_tags', []),
            'sub_headlines': data.get('h2_tags', [])[:5],
            'prices': data.get('prices_found', []),
            'positioning': self._extract_positioning(data)
        }
        
        return analysis
    
    def _extract_positioning(self, data):
        """Extrai elementos de posicionamento do conteúdo"""
        positioning = {
            'tagline': '',
            'value_proposition': '',
            'target_audience': ''
        }
        
        # Tentar extrair do título e descrição
        title = data.get('title', '')
        desc = data.get('description', '')
        
        if title:
            positioning['tagline'] = title.split('|')[0].strip()
        
        if desc:
            positioning['value_proposition'] = desc[:150]
        
        return positioning
    
    def search_market(self, query, competitor_urls=None):
        """
        Pesquisa completa de mercado
        
        Args:
            query: Termo de busca principal
            competitor_urls: Lista de URLs de concorrentes (opcional)
            
        Returns:
            Relatório de pesquisa
        """
        print(f"🔍 Pesquisando mercado: {query}")
        
        # Buscar informações gerais
        search_results = self.search_duckduckgo(query, max_results=15)
        
        # Analisar concorrentes
        competitor_analysis = []
        if competitor_urls:
            print(f"📊 Analisando {len(competitor_urls)} concorrentes...")
            for url in competitor_urls:
                analysis = self.analyze_competitor(url)
                competitor_analysis.append(analysis)
                time.sleep(1)  # Respeitar rate limit
        
        # Compilar relatório
        report = {
            'query': query,
            'search_results': search_results,
            'competitor_analysis': competitor_analysis,
            'summary': self._generate_summary(search_results, competitor_analysis)
        }
        
        return report
    
    def _generate_summary(self, search_results, competitor_analysis):
        """Gera resumo da pesquisa"""
        summary = {
            'total_results_found': len(search_results),
            'competitors_analyzed': len(competitor_analysis),
            'common_themes': [],
            'price_range': {'min': None, 'max': None},
            'key_insights': []
        }
        
        # Extrair preços
        all_prices = []
        for comp in competitor_analysis:
            prices = comp.get('prices', [])
            # Limpar e converter preços
            for p in prices:
                try:
                    clean = p.replace('R$', '').replace('.', '').replace(',', '.').strip()
                    if clean:
                        all_prices.append(float(clean))
                except:
                    pass
        
        if all_prices:
            summary['price_range'] = {
                'min': min(all_prices),
                'max': max(all_prices),
                'average': sum(all_prices) / len(all_prices)
            }
        
        return summary
    
    def generate_report(self, market_data, output_file='research_report.json'):
        """
        Gera relatório formatado
        
        Args:
            market_data: Dados da pesquisa
            output_file: Nome do arquivo de saída
        """
        # Salvar JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, ensure_ascii=False, indent=2)
        
        # Gerar markdown
        md_file = output_file.replace('.json', '.md')
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(market_data))
        
        print(f"✅ Relatório salvo: {output_file} e {md_file}")
        return output_file
    
    def _generate_markdown_report(self, data):
        """Gera relatório em formato markdown"""
        md = f"""# Research Report
## Query: {data.get('query', 'N/A')}

---

## Executive Summary

- **Resultados encontrados:** {len(data.get('search_results', []))}
- **Concorrentes analisados:** {len(data.get('competitor_analysis', []))}

---

## Search Results

"""
        for i, result in enumerate(data.get('search_results', [])[:10], 1):
            md += f"""### {i}. {result.get('title', 'N/A')}
**URL:** {result.get('url', 'N/A')}

{result.get('snippet', 'N/A')}

---

"""
        
        md += "## Competitor Analysis\n\n"
        for comp in data.get('competitor_analysis', []):
            md += f"""### {comp.get('url', 'N/A')}

**Title:** {comp.get('title', 'N/A')}

**Description:** {comp.get('description', 'N/A')}

**Main Headlines:**
"""
            for h1 in comp.get('main_headlines', []):
                md += f"- {h1}\n"
            
            md += f"""
**Prices Found:** {', '.join(comp.get('prices', [])[:5]) or 'N/A'}

---

"""
        
        summary = data.get('summary', {})
        md += f"""## Summary

### Price Analysis
- **Minimum:** R$ {summary.get('price_range', {}).get('min', 'N/A')}
- **Maximum:** R$ {summary.get('price_range', {}).get('max', 'N/A')}
- **Average:** R$ {summary.get('price_range', {}).get('average', 'N/A'):.2f}

---

*Report generated by Vibe Marketing Research Tools*
"""
        return md


def main():
    """Função principal para teste"""
    print("🚀 Vibe Marketing - Research Tools")
    print("=" * 50)
    
    research = MarketResearch()
    
    # Teste de busca
    query = input("\nDigite o termo de pesquisa: ")
    
    print(f"\n🔍 Buscando: {query}")
    results = research.search_duckduckgo(query, max_results=5)
    
    print(f"\n📊 Resultados encontrados: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   {result['url']}")
        print(f"   {result['snippet'][:100]}...")
    
    # Perguntar sobre concorrentes
    competitors = input("\nDigite URLs de concorrentes (separadas por vírgula) ou pressione Enter: ")
    
    if competitors:
        competitor_urls = [url.strip() for url in competitors.split(',')]
        
        print(f"\n📊 Analisando {len(competitor_urls)} concorrentes...")
        
        # Pesquisa completa
        report = research.search_market(query, competitor_urls)
        
        # Gerar relatório
        output_file = f"research_{query.replace(' ', '_')}.json"
        research.generate_report(report, output_file)
        
        print(f"\n✅ Pesquisa completa!")
        print(f"📄 Relatório salvo em: {output_file}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
