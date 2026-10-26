import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

/**
 * Basis-path tests for EligibilityCriteria. Node numbers refer to the control flow graphs:
 * parseBranches() has V(G) = 6 and getReasons() has V(G) = 9.
 * Students are the demo students of the USPS prototype.
 */
@DisplayName("Part 2 - EligibilityCriteria independent paths")
class EligibilityCriteriaTest {

    private static final Student AARAV = new Student("R23CS101", "CSE", "2023-2027", 8.60, 0);
    private static final Student KABIR = new Student("R23EC103", "ECE", "2023-2027", 6.80, 1);
    private static final Student ROHAN = new Student("R22ME105", "ME", "2022-2026", 7.90, 2);

    private static EligibilityCriteria rule(Double minCgpa, String branches, Integer maxBacklogs, String batch) {
        return new EligibilityCriteria(1, minCgpa, branches, maxBacklogs, batch);
    }

    @Nested
    @DisplayName("parseBranches()  V(G) = 6")
    @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
    class ParseBranches {

        @Test
        @Order(1)
        @DisplayName("R1: 1-2-3-12  no branches given (null)")
        void pathR1Null() {
            assertEquals(List.of(), EligibilityCriteria.parseBranches(null));
        }

        @Test
        @Order(2)
        @DisplayName("R2: 1-2-4-5-6-4-11-12  only a blank entry is skipped")
        void pathR2BlankSkipped() {
            assertEquals(List.of(), EligibilityCriteria.parseBranches("  "));
        }

        @Test
        @Order(3)
        @DisplayName("R3: 1-2-4-5-6-7-8-12  unknown branch refused")
        void pathR3UnknownBranch() {
            IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                    () -> EligibilityCriteria.parseBranches("AI"));
            assertEquals("Unknown branch AI.", e.getMessage());
        }

        @Test
        @Order(4)
        @DisplayName("R4: 1-2-4-5-6-7-9-10-4-11-12  one valid branch added")
        void pathR4OneBranch() {
            assertEquals(List.of("CSE"), EligibilityCriteria.parseBranches("CSE"));
        }

        @Test
        @Order(5)
        @DisplayName("R5: 1-2-4-...-9-10-4-5-6-7-9-4-11-12  duplicate kept once")
        void pathR5Duplicate() {
            assertEquals(List.of("CSE"), EligibilityCriteria.parseBranches("CSE, cse"));
        }

        @Test
        @Order(6)
        @DisplayName("Loop many times: ' it , CSE,,ece ' gives IT, CSE, ECE")
        void loopManyTimes() {
            assertEquals(List.of("IT", "CSE", "ECE"), EligibilityCriteria.parseBranches(" it , CSE,,ece "));
        }
    }

    @Nested
    @DisplayName("getReasons()  V(G) = 9")
    @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
    class GetReasons {

        @Test
        @Order(1)
        @DisplayName("A1: 1-2-5-8-11-14  no criterion set")
        void pathA1NoCriteria() {
            assertEquals(List.of(), rule(null, null, null, null).getReasons(KABIR));
        }

        @Test
        @Order(2)
        @DisplayName("A2: 1-2-3-5-8-11-14  CGPA 8.60 meets minimum 7.0")
        void pathA2CgpaMet() {
            assertEquals(List.of(), rule(7.0, null, null, null).getReasons(AARAV));
        }

        @Test
        @Order(3)
        @DisplayName("A3: 1-2-3-4-5-8-11-14  CGPA 6.80 below minimum 7.0")
        void pathA3CgpaBelow() {
            assertEquals(List.of("CGPA 6.80 is below the minimum 7.00."), rule(7.0, null, null, null).getReasons(KABIR));
        }

        @Test
        @Order(4)
        @DisplayName("A4: 1-2-5-6-8-11-14  branch CSE allowed")
        void pathA4BranchAllowed() {
            assertEquals(List.of(), rule(null, "CSE, IT", null, null).getReasons(AARAV));
        }

        @Test
        @Order(5)
        @DisplayName("A5: 1-2-5-6-7-8-11-14  branch ECE not allowed")
        void pathA5BranchNotAllowed() {
            assertEquals(List.of("Branch ECE is not in the allowed branches (CSE, IT)."),
                    rule(null, "CSE, IT", null, null).getReasons(KABIR));
        }

        @Test
        @Order(6)
        @DisplayName("A6: 1-2-5-8-9-11-14  1 backlog equals maximum 1")
        void pathA6BacklogsEqual() {
            assertEquals(List.of(), rule(null, null, 1, null).getReasons(KABIR));
        }

        @Test
        @Order(7)
        @DisplayName("A7: 1-2-5-8-9-10-11-14  1 backlog exceeds maximum 0")
        void pathA7BacklogsExceed() {
            assertEquals(List.of("Active backlogs 1 exceed the maximum 0."), rule(null, null, 0, null).getReasons(KABIR));
        }

        @Test
        @Order(8)
        @DisplayName("A8: 1-2-5-8-11-12-14  batch 2023-2027 matches")
        void pathA8BatchMatches() {
            assertEquals(List.of(), rule(null, null, null, "2023-2027").getReasons(AARAV));
        }

        @Test
        @Order(9)
        @DisplayName("A9: 1-2-5-8-11-12-13-14  batch 2022-2026 does not match")
        void pathA9BatchDiffers() {
            assertEquals(List.of("Batch 2022-2026 does not match the required batch 2023-2027."),
                    rule(null, null, null, "2023-2027").getReasons(ROHAN));
        }

        @Test
        @Order(10)
        @DisplayName("All four criteria fail together (job J-1 rules, student Rohan): reasons in order")
        void allCriteriaFail() {
            assertEquals(List.of("CGPA 7.90 is below the minimum 8.00.",
                            "Branch ME is not in the allowed branches (CSE, IT).",
                            "Active backlogs 2 exceed the maximum 0.",
                            "Batch 2022-2026 does not match the required batch 2023-2027."),
                    rule(8.0, "CSE, IT", 0, "2023-2027").getReasons(ROHAN));
        }

        @Test
        @Order(11)
        @DisplayName("Boundary: CGPA exactly equal to the minimum (7.00 vs 7.0) is eligible")
        void cgpaEqualsMinimum() {
            Student diya = new Student("R23IT102", "IT", "2023-2027", 7.00, 0);
            assertEquals(List.of(), rule(7.0, null, null, null).getReasons(diya));
        }
    }

    @Nested
    @DisplayName("Constructor")
    class Constructor {

        @Test
        @DisplayName("Branches text is parsed and the id kept: id 7, ' it, cse ' gives IT, CSE")
        void branchesParsed() {
            EligibilityCriteria c = new EligibilityCriteria(7, null, " it, cse ", null, null);
            assertEquals(7, c.getCriteriaId());
            assertEquals(List.of("IT", "CSE"), c.getAllowedBranches());
        }

        @Test
        @DisplayName("Blank batch '   ' means no batch criterion: Rohan (2022-2026) has no reason")
        void blankBatchIgnored() {
            assertEquals(List.of(), rule(null, null, null, "   ").getReasons(ROHAN));
        }
    }

    @Nested
    @DisplayName("evaluate()  V(G) = 1")
    class Evaluate {

        @Test
        @DisplayName("Eligible student: Aarav for J-1 (CGPA >= 7.0, CSE/IT, 0 backlogs, 2023-2027)")
        void eligible() {
            assertTrue(rule(7.0, "CSE, IT", 0, "2023-2027").evaluate(AARAV));
        }

        @Test
        @DisplayName("Ineligible student: Kabir for J-1")
        void ineligible() {
            assertFalse(rule(7.0, "CSE, IT", 0, "2023-2027").evaluate(KABIR));
        }
    }
}
