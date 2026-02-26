import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
  filename?: string;
};

export function buildMarkdownFilename(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") + ".md";
}

export function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ArtifactPreview({ content, filename }: Props) {
  const handleDownload = () => {
    const name = filename || "artefato.md";
    downloadMarkdown(content, buildMarkdownFilename(name));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-700">Preview</span>
        <button
          onClick={handleDownload}
          className="rounded bg-primary px-3 py-1 text-xs text-white hover:opacity-90"
        >
          Baixar .md
        </button>
      </div>
      <div className="prose prose-sm max-w-none rounded-lg border border-slate-200 bg-white p-4">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
