// Mock 1Health Pharmacy storefront — a realistic backdrop for the chat widget
// demo. Mirrors the real site's structure (header + nav, hero with prescription
// upload, category pills, product grid) using the brand palette. Self-contained:
// no external images (emoji/SVG/gradients only) so nothing can fail to load.

const CATEGORIES = [
  { icon: "💊", label: "Medicines" },
  { icon: "🧪", label: "Lab Tests" },
  { icon: "🩺", label: "Find Doctors" },
  { icon: "🧴", label: "Skin Care" },
  { icon: "🌿", label: "Wellness" },
  { icon: "👶", label: "Baby Care" },
];

const PRODUCTS = [
  { emoji: "💊", name: "Dolo 650 Tablet", pack: "Strip of 15 tablets", price: 31, mrp: 34, off: 9 },
  { emoji: "🧪", name: "Augmentin 625 Duo", pack: "Strip of 10 tablets", price: 150, mrp: 197, off: 24, rx: true },
  { emoji: "🟠", name: "Vitamin C Chewable", pack: "Bottle of 60", price: 285, mrp: 450, off: 36 },
  { emoji: "💊", name: "Zerodol-SP Tablet", pack: "Strip of 10 tablets", price: 118, mrp: 133, off: 11, rx: true },
  { emoji: "🧴", name: "Cetaphil Moisturiser", pack: "250 ml", price: 499, mrp: 625, off: 20 },
  { emoji: "🟢", name: "Shelcal 500 Tablet", pack: "Strip of 15 tablets", price: 105, mrp: 120, off: 12 },
  { emoji: "💧", name: "ORS Orange Powder", pack: "Pack of 5", price: 95, mrp: 110, off: 14 },
  { emoji: "🩹", name: "Digene Antacid Gel", pack: "200 ml", price: 148, mrp: 165, off: 10 },
];

function Rupee({ value }: { value: number }) {
  return <span>₹{value}</span>;
}

export default function DemoSite() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-ink">
      {/* Announcement bar */}
      <div className="bg-brand-700 text-center text-xs text-white/90 py-1.5 px-4">
        Flat 25% off on your first order + free delivery over ₹499 · Use code{" "}
        <span className="font-semibold">1HEALTH25</span>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-gray-100 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500 text-white shadow-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </div>
            <div className="leading-tight">
              <div className="text-lg font-bold text-brand-700">1Health</div>
              <div className="-mt-1 text-[10px] font-medium uppercase tracking-wide text-muted">
                Pharmacy
              </div>
            </div>
          </div>

          <button className="hidden items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-muted hover:bg-gray-50 sm:flex">
            📍 <span className="font-medium text-ink">Hyderabad</span> ▾
          </button>

          <div className="ml-auto hidden flex-1 max-w-md md:block">
            <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-muted">
              <span>🔍</span>
              <input
                className="w-full bg-transparent outline-none"
                placeholder="Search medicines & health products"
                readOnly
              />
            </div>
          </div>

          <nav className="ml-auto flex items-center gap-4 text-sm font-medium text-ink md:ml-0">
            <span className="hidden cursor-pointer hover:text-brand-600 lg:inline">Offers</span>
            <span className="cursor-pointer hover:text-brand-600">🛒 Cart</span>
            <button className="rounded-lg bg-brand-500 px-3.5 py-1.5 text-white transition-colors hover:bg-brand-600">
              Login
            </button>
          </nav>
        </div>

        <div className="border-t border-gray-100">
          <div className="mx-auto flex max-w-7xl items-center gap-6 overflow-x-auto px-4 py-2 text-sm text-ink">
            {["Buy Medicines", "Find Doctors", "Lab Tests", "Health Records", "Wellness", "Offers"].map(
              (item) => (
                <span key={item} className="cursor-pointer whitespace-nowrap hover:text-brand-600">
                  {item}
                </span>
              )
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-50 to-white">
        <div className="mx-auto grid max-w-7xl items-center gap-6 px-4 py-10 md:grid-cols-2 md:py-14">
          <div>
            <span className="inline-block rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700">
              Trusted by 2,00,000+ families
            </span>
            <h1 className="mt-4 text-3xl font-bold leading-tight text-ink md:text-4xl">
              Your Health, <span className="text-brand-600">Delivered</span> in
              hours
            </h1>
            <p className="mt-3 max-w-md text-sm text-muted">
              Genuine medicines, lab tests at home, and doctor consultations — all
              in one place. Upload your prescription and we'll do the rest.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button className="rounded-xl bg-brand-500 px-5 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-600">
                🛒 Order Medicines
              </button>
              <button className="rounded-xl border border-brand-200 bg-white px-5 py-3 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50">
                📄 Upload Prescription
              </button>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted">
              <span>✅ 100% genuine</span>
              <span>🚚 Express delivery</span>
              <span>💊 20,000+ products</span>
            </div>
          </div>

          <div className="relative hidden justify-center md:flex">
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: "💊", label: "Medicines" },
                { icon: "🧪", label: "Lab Tests" },
                { icon: "🩺", label: "Consult" },
                { icon: "🚚", label: "Delivery" },
              ].map((c) => (
                <div
                  key={c.label}
                  className="flex h-28 w-36 flex-col items-center justify-center gap-2 rounded-2xl bg-white shadow-sm"
                >
                  <span className="text-3xl">{c.icon}</span>
                  <span className="text-sm font-medium text-ink">{c.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Category pills */}
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          {CATEGORIES.map((c) => (
            <div
              key={c.label}
              className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border border-gray-100 bg-white p-4 text-center shadow-sm transition-transform hover:-translate-y-0.5"
            >
              <span className="text-2xl">{c.icon}</span>
              <span className="text-xs font-medium text-ink">{c.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Product grid */}
      <section className="mx-auto max-w-7xl px-4 pb-16">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-ink">🔥 Hot Sellers</h2>
          <span className="cursor-pointer text-sm font-medium text-brand-600">
            View all →
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {PRODUCTS.map((p) => (
            <div
              key={p.name}
              className="flex flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm transition-transform hover:-translate-y-1"
            >
              <div className="relative flex h-28 items-center justify-center bg-brand-50 text-4xl">
                {p.emoji}
                <span className="absolute left-2 top-2 rounded-md bg-brand-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {p.off}% OFF
                </span>
                {p.rx && (
                  <span className="absolute right-2 top-2 rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                    Rx
                  </span>
                )}
              </div>
              <div className="flex flex-1 flex-col p-3">
                <div className="text-sm font-semibold text-ink">{p.name}</div>
                <div className="mt-0.5 text-xs text-muted">{p.pack}</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-sm font-bold text-ink">
                    <Rupee value={p.price} />
                  </span>
                  <span className="text-xs text-muted line-through">
                    <Rupee value={p.mrp} />
                  </span>
                </div>
                <button className="mt-3 rounded-lg border border-brand-500 py-1.5 text-xs font-semibold text-brand-600 transition-colors hover:bg-brand-500 hover:text-white">
                  Add to Cart
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 text-sm text-muted">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-500 text-white">
                +
              </div>
              <span className="font-bold text-brand-700">1Health Pharmacy</span>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-1">
              <span>About</span>
              <span>Contact</span>
              <span>Privacy</span>
              <span>Terms</span>
            </div>
          </div>
          <div className="mt-4 text-xs text-muted/80">
            © 2026 1Health Pharmacy. Demo storefront — chatbot widget preview.
          </div>
        </div>
      </footer>
    </div>
  );
}
