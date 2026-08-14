import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  color?: 'gain' | 'loss' | 'default';
}

// DESIGN.md module — gray-50 fill, hairline border, square, small red header tab,
// mono value cell. `gain` = utility-red (attention), `loss` = faint ink (dormant).
export function MetricCard({ label, value, sub, color = 'default' }: MetricCardProps) {
  const colorClass =
    color === 'gain' ? 'text-red' :
    color === 'loss' ? 'text-faint' :
    'text-ink';

  return (
    <div className="flex flex-col border border-hairline bg-gray-50">
      <div className="border-b border-hairline px-3 py-1.5">
        <span className="tab-heading text-red">{label.toUpperCase()}</span>
      </div>
      <div className="px-3 py-2">
        <p className={cn('number-md', colorClass)}>{value}</p>
        {sub && <p className="caption mt-1 text-faint">{sub}</p>}
      </div>
    </div>
  );
}
