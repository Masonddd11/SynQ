import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SymbolPicker } from '../SymbolPicker';

const AVAILABLE = ['AAPL', 'MSFT', 'NVDA'];

describe('SymbolPicker', () => {
  it('renders a switch row per available symbol', () => {
    render(<SymbolPicker available={AVAILABLE} value={[]} onValueChange={vi.fn()} />);
    AVAILABLE.forEach((sym) => {
      expect(screen.getByText(sym)).toBeInTheDocument();
    });
  });

  it('shows selected symbols as checked even when not in available (custom syms)', () => {
    render(
      <SymbolPicker available={AVAILABLE} value={['IREN']} onValueChange={vi.fn()} />
    );
    expect(screen.getByText('IREN')).toBeInTheDocument();
  });

  it('selects all available symbols when Select all is clicked', () => {
    const onChange = vi.fn();
    render(<SymbolPicker available={AVAILABLE} value={[]} onValueChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /select all/i }));
    expect(onChange).toHaveBeenCalledWith(AVAILABLE);
  });

  it('clears selection when Clear all is clicked', () => {
    const onChange = vi.fn();
    render(<SymbolPicker available={AVAILABLE} value={AVAILABLE} onValueChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /clear all/i }));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('filters by sector chip, keeping only matching symbols', () => {
    const meta = {
      AAPL: { sector: 'Information Technology' },
      MSFT: { sector: 'Information Technology' },
      NVDA: { sector: 'Consumer Discretionary' },
    };
    render(
      <SymbolPicker
        available={AVAILABLE}
        value={[]}
        onValueChange={vi.fn()}
        meta={meta}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /information technology/i }));
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
  });
});
