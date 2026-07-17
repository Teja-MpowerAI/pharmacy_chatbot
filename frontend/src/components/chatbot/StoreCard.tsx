interface Store {
  index: number;
  name: string;
  address?: string;
  phone?: string;
  hours?: string | null;
  available_count?: number;
  total_medicines?: number;
  total_price?: number;
  all_available?: boolean;
  recommended?: boolean;
}

interface Props {
  store: Store;
  selectable: boolean;
  onSelect: () => void;
}

function money(v?: number) {
  if (v === undefined || v === null) return "";
  return Number.isInteger(v) ? `₹${v}` : `₹${v.toFixed(2)}`;
}

export default function StoreCard({ store, selectable, onSelect }: Props) {
  return (
    <div
      className={`rounded-xl border bg-white p-3 shadow-sm transition-colors ${
        store.recommended ? "border-brand-400 ring-1 ring-brand-200" : "border-gray-100"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
            {store.index}
          </span>
          <span className="text-sm font-semibold text-gray-800">{store.name}</span>
        </div>
        {store.recommended && (
          <span className="shrink-0 rounded-full bg-brand-500 px-2 py-0.5 text-[10px] font-semibold text-white">
            ⭐ Recommended
          </span>
        )}
      </div>

      <div className="mt-1.5 space-y-0.5 text-xs text-gray-500">
        {store.address && <div>📍 {store.address}</div>}
        {store.phone && <div>📞 {store.phone}</div>}
        {store.hours && <div>🕒 {store.hours}</div>}
      </div>

      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">
          📦 {store.available_count}/{store.total_medicines} available
          {store.total_price ? ` · ${money(store.total_price)}` : ""}
        </span>
        {selectable && (
          <button
            onClick={onSelect}
            className="rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white transition-colors hover:bg-brand-600 active:scale-95"
          >
            Select
          </button>
        )}
      </div>
    </div>
  );
}
