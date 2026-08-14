'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  active?: boolean;
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Backtest',
    items: [
      { href: '/', label: 'History' },
      { href: '/new', label: 'New Backtest' },
      { href: '/analysis', label: 'Analysis' },
      { href: '/data', label: 'Data' },
    ],
  },
  {
    title: 'Trading',
    items: [
      { href: '/live/paper', label: 'Paper Trading' },
      { href: '/live/real', label: 'Live Trading' },
    ],
  },
  {
    title: 'System',
    items: [
      { href: '/status', label: 'Services Health' },
      { href: '/terminal', label: 'Terminal' },
      { href: '/settings', label: 'Settings' },
    ],
  },
];

function isItemActive(pathname: string, item: NavItem): boolean {
  if (item.href === '/') {
    return pathname === '/' || pathname.startsWith('/sessions/');
  }
  if (item.active !== undefined) return item.active;
  return pathname === item.href;
}

function BrandMark() {
  return (
    <Link href="/" className="flex items-center gap-2 shrink-0">
      <span
        aria-hidden
        className="flex h-8 w-8 items-center justify-center bg-red text-white"
      >
        <span className="text-xs font-bold tracking-tight">JS</span>
      </span>
      <span className="module-title text-ink">JINGS STREET</span>
    </Link>
  );
}

function NavList({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-5 overflow-y-auto">
      {NAV_SECTIONS.map((section) => (
        <div key={section.title}>
          <p className="caption px-3 pb-1.5 text-faint">{section.title.toUpperCase()}</p>
          <ul className="space-y-px">
            {section.items.map((item) => {
              const active = isItemActive(pathname, item);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={cn(
                      'flex items-center gap-2 border-l-2 px-3 py-2 text-xs font-semibold tracking-[0.01em] transition-colors',
                      active
                        ? 'border-red bg-red-soft text-red'
                        : 'border-transparent text-ink hover:bg-gray-100 hover:text-ink',
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Mobile top bar — hamburger opens the rail as a drawer */}
      <header className="sticky top-0 z-40 flex h-12 items-center justify-between border-b border-hairline bg-background px-4 md:hidden">
        <BrandMark />
        <button
          type="button"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
          className="flex h-8 w-8 items-center justify-center border border-hairline text-ink"
        >
          <span className="text-sm leading-none">{menuOpen ? '✕' : '☰'}</span>
        </button>
      </header>

      {menuOpen && (
        <button
          type="button"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-40 bg-ink/40 md:hidden"
        />
      )}

      {/* Persistent left nav rail */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-hairline bg-background transition-transform md:translate-x-0',
          menuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-between border-b border-hairline px-3 py-4">
          <BrandMark />
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
            className="flex h-7 w-7 items-center justify-center text-faint md:hidden"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 px-2 py-4">
          <NavList pathname={pathname} onNavigate={() => setMenuOpen(false)} />
        </div>
        <p className="caption border-t border-hairline px-4 py-3 text-faint">
          AUTONOMOUS TRADING AGENT
        </p>
      </aside>

      {/* Full-width mosaic surface — no max-width softness */}
      <main className="md:pl-[260px]">
        <div className="p-4 md:p-5">{children}</div>
      </main>
    </div>
  );
}
