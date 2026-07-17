interface Medicine {
  name: string;
  dosage?: string;
  frequency?: string;
  duration?: string;
  quantity?: number | string;
}

interface Prescription {
  patient_name?: string | null;
  doctor_name?: string | null;
  hospital_name?: string | null;
  prescription_date?: string | null;
  medicines?: Medicine[];
  image_url?: string;
}

export default function PrescriptionView({ data }: { data: Prescription }) {
  const meds = data.medicines || [];
  return (
    <div className="rounded-xl border border-brand-100 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-brand-700">
        📄 Prescription Read
      </div>

      {data.image_url && (
        <a href={data.image_url} target="_blank" rel="noopener noreferrer">
          <img
            src={data.image_url}
            alt="Prescription"
            className="mb-2 max-h-40 w-full rounded-lg object-cover"
          />
        </a>
      )}

      {(data.patient_name || data.doctor_name || data.prescription_date) && (
        <div className="mb-2 space-y-0.5 rounded-lg bg-brand-50 p-2 text-xs text-gray-600">
          {data.patient_name && <div>👤 Patient: {data.patient_name}</div>}
          {data.doctor_name && <div>🩺 Doctor: {data.doctor_name}</div>}
          {data.hospital_name && <div>🏥 {data.hospital_name}</div>}
          {data.prescription_date && <div>📅 {data.prescription_date}</div>}
        </div>
      )}

      <ul className="space-y-1.5">
        {meds.map((m, i) => (
          <li key={i} className="rounded-lg border border-gray-100 p-2 text-xs">
            <div className="font-semibold text-gray-800">
              {i + 1}. {m.name}
            </div>
            <div className="mt-0.5 text-gray-500">
              {[
                m.dosage && `💊 ${m.dosage}`,
                m.frequency && `🔁 ${m.frequency}`,
                m.duration && `⏳ ${m.duration}`,
                m.quantity && `📦 ${m.quantity}`,
              ]
                .filter(Boolean)
                .join("  ·  ")}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
