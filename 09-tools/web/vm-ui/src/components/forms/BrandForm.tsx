import { useState, type FormEvent } from "react";
import { BrandApi } from "../../api/typed-client";
import type { BrandCreateRequest, BrandUpdateRequest } from "../../types/api";

interface BrandFormProps {
  initialData?: {
    brand_id?: string;
    name: string;
    description?: string;
  };
  onSuccess?: () => void;
  onCancel?: () => void;
}

interface FormErrors {
  name?: string;
  general?: string;
}

export default function BrandForm({
  initialData,
  onSuccess,
  onCancel,
}: BrandFormProps): JSX.Element {
  const isEditing = !!initialData?.brand_id;

  const [name, setName] = useState(initialData?.name ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Brand name is required";
    } else if (name.trim().length < 2) {
      newErrors.name = "Brand name must be at least 2 characters";
    } else if (name.trim().length > 100) {
      newErrors.name = "Brand name must be less than 100 characters";
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
      if (isEditing && initialData?.brand_id) {
        // Update existing brand
        const payload: BrandUpdateRequest = {
          name: name.trim(),
        };
        await BrandApi.updateBrand(initialData.brand_id, payload);
      } else {
        // Create new brand
        const payload: BrandCreateRequest = {
          name: name.trim(),
        };
        await BrandApi.createBrand(payload);
      }

      onSuccess?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save brand";
      setErrors({ general: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBlur = (field: string): void => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    validate();
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
          htmlFor="brand-name"
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Brand Name <span className="text-red-500">*</span>
        </label>
        <input
          id="brand-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => handleBlur("name")}
          placeholder="Enter brand name"
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

      {/* Description Field */}
      <div>
        <label
          htmlFor="brand-description"
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Description
        </label>
        <textarea
          id="brand-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter brand description (optional)"
          rows={3}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 placeholder-slate-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          disabled={isSubmitting}
        />
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
          {isEditing ? "Update Brand" : "Create Brand"}
        </button>
      </div>
    </form>
  );
}

// Hook for brand form state management
export function useBrandForm(initialName = "") {
  const [name, setName] = useState(initialName);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Brand name is required";
    } else if (name.trim().length < 2) {
      newErrors.name = "Brand name must be at least 2 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const submit = async (): Promise<boolean> => {
    if (!validate()) return false;

    setIsSubmitting(true);
    try {
      await BrandApi.createBrand({ name: name.trim() });
      setName("");
      setErrors({});
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create brand";
      setErrors({ general: message });
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    name,
    setName,
    errors,
    isSubmitting,
    validate,
    submit,
  };
}
