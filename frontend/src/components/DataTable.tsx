import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface ColumnDef<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  page?: number;
  totalCount?: number;
  pageSize?: number;
  onPageChange?: (nextPage: number) => void;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyTitle = "No records found",
  emptyDescription = "Adjust your search or filters, or create a new record.",
  page = 1,
  totalCount = rows.length,
  pageSize = 20,
  onPageChange,
}: DataTableProps<T>) {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600 ${
                    col.className || ""
                  }`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center text-slate-500">
                  Loading records...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center">
                  <div className="text-sm font-medium text-slate-800">{emptyTitle}</div>
                  <div className="text-xs text-slate-500 mt-1">{emptyDescription}</div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={rowKey(row)} className="hover:bg-slate-50/70 transition-colors">
                  {columns.map((col) => (
                    <td key={col.key} className={`px-4 py-3 align-middle ${col.className || ""}`}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {onPageChange && totalCount > 0 && (
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <span>
            Showing page <strong className="text-slate-900">{page}</strong> of{" "}
            <strong className="text-slate-900">{totalPages}</strong> ({totalCount} total)
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Prev
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

