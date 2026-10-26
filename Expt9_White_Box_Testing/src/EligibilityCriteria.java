import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Part 2: eligibility rule-set of a job (class EligibilityCriteria of the Expt-3 class diagram of the
 * Unified Student Placement System, SRS FR-13 / FR-14, BR-03). A criterion that is not set (null or
 * no branches) is not checked. The PBL prototype applies the same rules in Python (app/rules.py).
 */
public class EligibilityCriteria {

    public static final List<String> BRANCHES = List.of("CSE", "IT", "ECE", "EE", "ME", "CE");

    private final int criteriaId;
    private final Double minCgpa;
    private final List<String> allowedBranches;
    private final Integer maxBacklogs;
    private final String batch;

    public EligibilityCriteria(int criteriaId, Double minCgpa, String allowedBranches, Integer maxBacklogs,
                               String batch) {
        this.criteriaId = criteriaId;
        this.minCgpa = minCgpa;
        this.allowedBranches = parseBranches(allowedBranches);
        this.maxBacklogs = maxBacklogs;
        this.batch = (batch == null || batch.isBlank()) ? null : batch.trim();
    }

    /** Turns "cse, IT" into [CSE, IT]: blanks are skipped, duplicates kept once, unknown branches refused. */
    public static List<String> parseBranches(String text) {
        List<String> branches = new ArrayList<>();
        if (text == null) {
            return branches;
        }
        for (String part : text.split(",")) {
            String branch = part.trim().toUpperCase(Locale.ROOT);
            if (branch.isEmpty()) {
                continue;
            }
            if (!BRANCHES.contains(branch)) {
                throw new IllegalArgumentException("Unknown branch " + branch + ".");
            }
            if (!branches.contains(branch)) {
                branches.add(branch);
            }
        }
        return branches;
    }

    /** getReasons(): every criterion the student does not meet, in the order CGPA, branch, backlogs, batch. */
    public List<String> getReasons(Student s) {
        List<String> reasons = new ArrayList<>();
        if (minCgpa != null) {
            if (s.getCgpa() < minCgpa) {
                reasons.add(String.format(Locale.ROOT, "CGPA %.2f is below the minimum %.2f.", s.getCgpa(), minCgpa));
            }
        }
        if (!allowedBranches.isEmpty()) {
            if (!allowedBranches.contains(s.getDepartment())) {
                reasons.add("Branch " + s.getDepartment() + " is not in the allowed branches ("
                        + String.join(", ", allowedBranches) + ").");
            }
        }
        if (maxBacklogs != null) {
            if (s.getBacklogs() > maxBacklogs) {
                reasons.add("Active backlogs " + s.getBacklogs() + " exceed the maximum " + maxBacklogs + ".");
            }
        }
        if (batch != null) {
            if (!batch.equals(s.getBatch())) {
                reasons.add("Batch " + s.getBatch() + " does not match the required batch " + batch + ".");
            }
        }
        return reasons;
    }

    /** evaluate(): the student is eligible when no criterion is unmet. */
    public boolean evaluate(Student s) {
        return getReasons(s).isEmpty();
    }

    public int getCriteriaId() {
        return criteriaId;
    }

    public List<String> getAllowedBranches() {
        return allowedBranches;
    }
}
