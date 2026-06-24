interface CompareButtonProps {
  isLoading: boolean;
  disabled?: boolean;
  isPrimary?: boolean;
  onClick: () => void;
}

export function CompareButton({
  isLoading,
  disabled = false,
  isPrimary = false,
  onClick,
}: CompareButtonProps) {
  const isDisabled = disabled || isLoading;
  const className = ["compare-button", isPrimary && !isDisabled ? "action-primary" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      className={className}
      type="button"
      disabled={isDisabled}
      aria-busy={isLoading}
      onClick={onClick}
    >
      {isLoading ? "Comparing..." : "Compare drawings"}
    </button>
  );
}
