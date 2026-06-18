# Outlier investigation: comparison-569dd276

## Question

Why did `comparison-569dd276e92f48beb5ee3129b8c7b3d1.png` show **64.6% changed** and **18% magenta of changed** while canonical **0A vs 0B** runs show **21.3% changed**?

## Finding

**Not an alignment failure.** The outlier profile matches **cross-series revision compares** (different model stages), not 0A/0B.

| Pair | Changed % | Magenta % of changed | Inlier ratio | Confidence |
|------|-----------|----------------------|--------------|------------|
| **0A vs 0B** (smoke pair) | 21.3 | 5.7 | 0.804 | high |
| **1A vs 2A** (closest match to outlier) | 64.5 | 17.9 | 0.830 | high |
| 0B vs 1B | 62.4 | 16.4 | 0.832 | high |
| 0A vs 1A | 60.0 | 22.5 | 0.848 | high |
| 0A vs 2A | 86.9 | 4.9 | 0.864 | high |

The old `569dd276` PNG (green=92,950; changed=169,828; 64.6%) aligns with **1A vs 2A**-class compares where sheets share layout family but differ substantially in content.

## Conclusion

- Pipeline behaved correctly: homography succeeded, overlap gate passed, confidence **high**.
- High red/blue/magenta counts reflect **comparing different revision stages** (0 vs 1 vs 2 vs 3), not a bug in Pass 1.
- For coordination review, compare **same letter pair** (0A/0B, 1A/1B, etc.) from the same drawing issue.

## Recommendation

Document in smoke-test.md that cross-number compares (e.g. 1A vs 2A) are expected to show large change ratios and are not smoke sign-off pairs.
