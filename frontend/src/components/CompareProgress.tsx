export const COMPARE_PROGRESS_STAGES = [
  { id: "queued", label: "Queued" },
  { id: "loading_drawings", label: "Loading your drawings" },
  { id: "aligning_sheets", label: "Aligning the two sheets" },
  { id: "preparing_comparison", label: "Preparing the comparison area" },
  { id: "building_overlay", label: "Building the change overlay" },
  { id: "saving_results", label: "Saving your results" },
] as const;

export type CompareStageId =
  | (typeof COMPARE_PROGRESS_STAGES)[number]["id"]
  | "completed"
  | "failed";

interface CompareProgressProps {
  stage: CompareStageId | null;
}

export function CompareProgress({ stage }: CompareProgressProps) {
  const activeIndex = COMPARE_PROGRESS_STAGES.findIndex((item) => item.id === stage);
  const resolvedIndex = activeIndex >= 0 ? activeIndex : stage === "queued" ? 0 : -1;

  return (
    <ol className="compare-progress" aria-label="Comparison progress">
      {COMPARE_PROGRESS_STAGES.map((item, index) => {
        const isComplete = resolvedIndex > index;
        const isActive = resolvedIndex === index;
        const state = isComplete ? "complete" : isActive ? "active" : "pending";

        return (
          <li
            key={item.id}
            className={`compare-progress__step compare-progress__step--${state}`}
            aria-current={isActive ? "step" : undefined}
          >
            {item.label}
          </li>
        );
      })}
    </ol>
  );
}
