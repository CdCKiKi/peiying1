/**
 * 页面头部组件
 */
interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex justify-between gap-3 items-center">
      <div>
        {eyebrow && (
          <p className="text-[#a55b2a] text-sm font-bold mb-1">{eyebrow}</p>
        )}
        <h2 className="text-2xl font-bold">{title}</h2>
        {description && (
          <p className="text-[#667085] mt-1">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex gap-2 items-center flex-wrap">{actions}</div>
      )}
    </div>
  );
}
