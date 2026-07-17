import { Fragment } from "react";

interface Props {
  role: "user" | "bot";
  content: string;
  image?: string;
}

// Render the backend's light markdown: *bold* segments and newlines.
function renderContent(text: string) {
  return text.split("\n").map((line, li) => {
    const parts = line.split(/(\*[^*]+\*)/g).filter(Boolean);
    return (
      <Fragment key={li}>
        {parts.map((p, pi) =>
          p.startsWith("*") && p.endsWith("*") ? (
            <strong key={pi} className="font-semibold">
              {p.slice(1, -1)}
            </strong>
          ) : (
            <Fragment key={pi}>{p}</Fragment>
          )
        )}
        {li < text.split("\n").length - 1 && <br />}
      </Fragment>
    );
  });
}

export default function MessageBubble({ role, content, image }: Props) {
  const isUser = role === "user";
  // An image-only bubble (uploaded prescription) gets tighter padding.
  const onlyImage = image && !content;
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] overflow-hidden whitespace-pre-wrap break-words rounded-2xl text-sm leading-relaxed shadow-sm ${
          onlyImage ? "p-1" : "px-3.5 py-2.5"
        } ${
          isUser
            ? "rounded-br-sm bg-brand-500 text-white"
            : "rounded-bl-sm bg-white text-gray-800"
        }`}
      >
        {image && (
          <img
            src={image}
            alt="Uploaded prescription"
            className="max-h-56 w-full rounded-xl object-cover"
          />
        )}
        {content && (
          <div className={image ? "px-2 pb-1 pt-2" : ""}>{renderContent(content)}</div>
        )}
      </div>
    </div>
  );
}
