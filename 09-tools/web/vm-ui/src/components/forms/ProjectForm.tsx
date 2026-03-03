import { useState, type FormEvent } from "react";
import { ProjectApi } from "../../api/typed-client";
import type {
  ProjectCreateRequest,
  ProjectUpdateRequest,
} from "../../types/api";

interface ProjectFormProps {
  brandId: string;
  initialData?: {
    project_id?: string;
    name: string;
    objective?: string;
    channels?: string[];
  };
  onSuccess?: () => void;
  onCancel?: () => void;
}

interface FormErrors {
  name?: string;
  objective?: string;
  general?: string;
}

const CHANNEL_OPTIONS = [
  { value: "blog", label: "Blog" },
  { value: "social", label: "Social Media" },
  { value: "email", label: "Email Marketing" },
  { value: "ads", label: "Paid Ads" },
  { value: "landing", label: "Landing Pages" },
  { value: "video", label: "Video" },
];

export default function ProjectForm({
  brandId,
  initialData,
  onSuccess,
  onCancel,
}: ProjectFormProps): JSX.Element {
  const isEditing = !!initialData?.project_id;

  const [name, setName] = useState(initialData?.name ?? "");
  const [objective, setObjective] = useState(initialData?.objective ?? "");
  const [channels, setChannels] = useState<string[]>(
    initialData?.channels ?? []
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Project name is required";
    } else if (name.trim().length < 2) {
      newErrors.name = "Project name must be at least 2 characters";
    } else if (name.trim().length > 100) {
      newErrors.name = "Project name must be less than 100 characters";
    }

    if (objective && objective.length > 500) {
      newErrors.objective = "Objective must be less than 500 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent): Promise<void> => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      if (isEditing && initialData?.project_id) {
        // Update existing project
        const payload: ProjectUpdateRequest = {
          name: name.trim(),
          objective: objective.trim() || undefined,
          channels: channels.length > 0 ? channels : undefined,
        };
        await ProjectApi.updateProject(initialData.project_id, payload);
      } else {
        // Create new project
        const payload: ProjectCreateRequest = {
          brand_id: brandId,
          name: name.trim(),
          objective: objective.trim() || undefined,
          channels: channels.length > 0 ? channels : undefined,
        };
        await ProjectApi.createProject(payload);
      }

      onSuccess?.();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to save project";
      setErrors({ general: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBlur = (field: string): void => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    validate();
  };

  const toggleChannel = (channel: string): void => {
    setChannels((prev) =>
      prev.includes(channel)
        ? prev.filter((c) => c !== channel)
        : [...prev, channel]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* General Error */}
      {errors.general && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {errors.general}
        </div>
      )}

      {/* Name Field */}
      <div>
        <label
          htmlFor="project-name"
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Project Name <span className="text-red-500">*</span>
        </label>
        <input
          id="project-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => handleBlur("name")}
          placeholder="Enter project name"
          className={`w-full rounded-lg border px-3 py-2 text-slate-900 placeholder-slate-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary ${
            errors.name && touched.name
              ? "border-red-300 bg-red-50"
              : "border-slate-300"
          }`}
          disabled={isSubmitting}
        />
        {errors.name && touched.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name}</p>
        )}
      </div>

      {/* Objective Field */}
      <div>
        <label
          htmlFor="project-objective"
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Objective
        </label>
        <textarea
          id="project-objective"
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          onBlur={() => handleBlur("objective")}
          placeholder="Describe the project objective"
          rows={3}
          className={`w-full rounded-lg border px-3 py-2 text-slate-900 placeholder-slate-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary ${
            errors.objective && touched.objective
              ? "border-red-300 bg-red-50"
              : "border-slate-300"
          }`}
          disabled={isSubmitting}
        />
        {errors.objective && touched.objective && (
          <p className="mt-1 text-sm text-red-600">{errors.objective}</p>
        )}
        <p className="mt-1 text-xs text-slate-500">
          {objective.length}/500 characters
        </p>
      </div>

      {/* Channels Field */}
      <div>
        <label className="mb-2 block text-sm font-medium text-slate-700">
          Channels
        </label>
        <div className="flex flex-wrap gap-2">
          {CHANNEL_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => toggleChannel(option.value)}
              disabled={isSubmitting}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                channels.includes(option.value)
                  ? "bg-primary text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              } disabled:opacity-50`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmitting && (
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
          )}
          {isEditing ? "Update Project" : "Create Project"}
        </button>
      </div>
    </form>
  );
}

// Hook for project form state management
export function useProjectForm(brandId: string, initialName = "") {
  const [name, setName] = useState(initialName);
  const [objective, setObjective] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Project name is required";
    } else if (name.trim().length < 2) {
      newErrors.name = "Project name must be at least 2 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const submit = async (): Promise<boolean> => {
    if (!validate()) return false;

    setIsSubmitting(true);
    try {
      await ProjectApi.createProject({
        brand_id: brandId,
        name: name.trim(),
        objective: objective.trim() || undefined,
        channels: channels.length > 0 ? channels : undefined,
      });
      setName("");
      setObjective("");
      setChannels([]);
      setErrors({});
      return true;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create project";
      setErrors({ general: message });
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    name,
    setName,
    objective,
    setObjective,
    channels,
    setChannels,
    errors,
    isSubmitting,
    validate,
    submit,
  };
}
