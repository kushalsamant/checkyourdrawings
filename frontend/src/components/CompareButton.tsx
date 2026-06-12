interface CompareButtonProps {
  isLoading: boolean;
  disabled?: boolean;
  onClick: () => void;
}

export function CompareButton({
  isLoading,
  disabled = false,
  onClick,
}: CompareButtonProps) {
  const isDisabled = disabled || isLoading;

  return (
    <button
      className="compare-button"
      type="button"
      disabled={isDisabled}
      aria-busy={isLoading}
      onClick={onClick}
    >
      {isLoading ? "Comparing..." : "Compare drawings"}
    </button>
  );
}
