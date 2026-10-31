export default function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">{title}</h1>
      <div className="bg-white border border-slate-200 rounded-xl p-8 text-slate-500">
        {title} page coming soon.
      </div>
    </div>
  );
}