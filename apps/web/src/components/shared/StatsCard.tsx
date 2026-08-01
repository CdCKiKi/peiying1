/**
 * 统计卡片 - 对标 HTML Demo 的 stat 样式
 */
interface StatsCardProps {
  label: string;
  value: string | number;
  className?: string;
}

export function StatsCard({ label, value, className }: StatsCardProps) {
  return (
    <div
      className={`bg-white border border-[#d8dee6] rounded-lg p-3 shadow-[0_10px_30px_rgba(16,24,40,0.08)] ${className || ""}`}
    >
      <span className="block text-[#667085] text-sm">{label}</span>
      <strong className="block mt-1 text-2xl">{value}</strong>
    </div>
  );
}

interface StatsGridProps {
  items: { label: string; value: string | number }[];
}

export function StatsGrid({ items }: StatsGridProps) {
  return (
    <div className="grid grid-cols-4 gap-2.5">
      {items.map((item) => (
        <StatsCard key={item.label} label={item.label} value={item.value} />
      ))}
    </div>
  );
}
