interface Props {
  link: string;
  onPaid: () => void;
}

export default function PaymentButton({ link, onPaid }: Props) {
  return (
    <div className="space-y-2 rounded-xl border border-brand-100 bg-white p-3 shadow-sm">
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
      >
        💳 Pay Securely
      </a>
      <button
        onClick={onPaid}
        className="w-full rounded-lg border border-brand-200 px-4 py-2 text-xs font-medium text-brand-700 transition-colors hover:bg-brand-50"
      >
        I've completed the payment
      </button>
      <p className="text-center text-[10px] text-gray-400">
        Pay via UPI, Card, Netbanking or Wallet · Powered by Razorpay
      </p>
    </div>
  );
}
