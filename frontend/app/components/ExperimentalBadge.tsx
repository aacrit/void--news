import "../styles/experimental.css";

/* ---------------------------------------------------------------------------
   ExperimentalBadge — small mono pill reading "experimental". Sits beside the
   masthead wordmark so the posture is clear on every load. Purely decorative
   text, so it carries a title but no interactive role.
   --------------------------------------------------------------------------- */

interface ExperimentalBadgeProps {
  className?: string;
}

export default function ExperimentalBadge({ className }: ExperimentalBadgeProps) {
  return (
    <span
      className={`exp-badge${className ? ` ${className}` : ""}`}
      title="void --news is experimental"
    >
      experimental
    </span>
  );
}
