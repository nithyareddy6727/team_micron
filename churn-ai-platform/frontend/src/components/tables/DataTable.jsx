import { useMemo, useRef, useState } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { EmptyState } from '@/components/ui/EmptyState'

export function DataTable({
  columns,
  data,
  getRowId,
  onRowClick,
  emptyTitle = 'No rows available',
  emptyDescription = 'There is no live data to display yet.',
  height = 560,
  initialSorting = [],
}) {
  const [sorting, setSorting] = useState(initialSorting)
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    getRowId,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    debugTable: false,
  })

  const rows = table.getRowModel().rows
  const parentRef = useRef(null)
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 12,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()
  const gridTemplateColumns = columns.map((column) => column.meta?.width || 'minmax(0, 1fr)').join(' ')

  const headerGroups = useMemo(() => table.getHeaderGroups(), [table])

  if (!data.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/25">
      <div ref={parentRef} style={{ height }} className="overflow-auto">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm text-slate-200">
          <thead className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur">
            {headerGroups.map((headerGroup) => (
              <tr key={headerGroup.id} style={{ display: 'grid', gridTemplateColumns }}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="border-b border-white/10 px-4 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300"
                  >
                    {header.isPlaceholder ? null : (
                      <button
                        type="button"
                        className={`flex items-center gap-2 ${header.column.getCanSort() ? 'cursor-pointer select-none' : ''}`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {{ asc: '↑', desc: '↓' }[header.column.getIsSorted()] ?? null}
                      </button>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} style={{ height: totalSize, position: 'relative', padding: 0 }}>
                {virtualRows.map((virtualRow) => {
                  const row = rows[virtualRow.index]
                  return (
                    <div
                      key={row.id}
                      className="absolute left-0 top-0 w-full border-b border-white/5 hover:bg-white/5"
                      style={{ transform: `translateY(${virtualRow.start}px)` }}
                    >
                      <button
                        type="button"
                        onClick={() => onRowClick?.(row.original)}
                        className="grid w-full gap-0 text-left"
                        style={{ gridTemplateColumns }}
                      >
                        {row.getVisibleCells().map((cell) => (
                          <div key={cell.id} className="px-4 py-4 text-sm text-slate-100">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </div>
                        ))}
                      </button>
                    </div>
                  )
                })}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
