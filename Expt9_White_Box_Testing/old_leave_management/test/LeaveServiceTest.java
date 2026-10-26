import static org.junit.jupiter.api.Assertions.assertEquals;

import java.time.LocalDate;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

/**
 * Basis-path tests for LeaveService. Node numbers refer to the control flow graphs:
 * countLeaveDays() has V(G) = 3 and processRequest() has V(G) = 8.
 * Dates used: 01-11-2026 is a Sunday, 02-11-2026 is a Monday.
 */
@DisplayName("Part 2 - LeaveService independent paths")
class LeaveServiceTest {

    private static final LocalDate SAT_31_OCT = LocalDate.of(2026, 10, 31);
    private static final LocalDate SUN_01_NOV = LocalDate.of(2026, 11, 1);
    private static final LocalDate MON_02_NOV = LocalDate.of(2026, 11, 2);

    private LeaveService service;
    private Faculty permanent;
    private Faculty contract;

    @BeforeEach
    void setUp() {
        service = new LeaveService();
        permanent = new Faculty("FAC101", "PERMANENT", 8, 10, 7);
        contract = new Faculty("FAC102", "CONTRACT", 5, 0, 5);
    }

    @Nested
    @DisplayName("countLeaveDays()  V(G) = 3")
    @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
    class CountLeaveDays {

        @Test
        @Order(1)
        @DisplayName("Q1: 1-2-6  loop not entered (To date before From date)")
        void pathQ1LoopNotEntered() {
            assertEquals(0, service.countLeaveDays(MON_02_NOV, SUN_01_NOV));
        }

        @Test
        @Order(2)
        @DisplayName("Q2: 1-2-3-4-5-2-6  one working day")
        void pathQ2OneWorkingDay() {
            assertEquals(1, service.countLeaveDays(MON_02_NOV, MON_02_NOV));
        }

        @Test
        @Order(3)
        @DisplayName("Q3: 1-2-3-5-2-6  one Sunday (not counted)")
        void pathQ3OneSunday() {
            assertEquals(0, service.countLeaveDays(SUN_01_NOV, SUN_01_NOV));
        }

        @Test
        @Order(4)
        @DisplayName("Loop many times: Mon 02-11 to Sun 08-11 = 6 days")
        void loopOverFullWeek() {
            assertEquals(6, service.countLeaveDays(MON_02_NOV, LocalDate.of(2026, 11, 8)));
        }
    }

    @Nested
    @DisplayName("processRequest()  V(G) = 8")
    @TestMethodOrder(MethodOrderer.OrderAnnotation.class)
    class ProcessRequest {

        @Test
        @Order(1)
        @DisplayName("P1: 1-2-10-12-14-16-17  CL approved")
        void pathP1CasualLeaveApproved() {
            assertEquals("APPROVED: 2 day(s) of CL, balance left 6",
                    service.processRequest(permanent, "CL", MON_02_NOV, MON_02_NOV.plusDays(1)));
            assertEquals(6, permanent.getBalance("CL"));
        }

        @Test
        @Order(2)
        @DisplayName("P2: 1-3-4-5-17  ML requested by contract faculty")
        void pathP2ContractFacultyMedicalLeave() {
            assertEquals("REJECTED: contract faculty are not eligible for ML",
                    service.processRequest(contract, "ML", MON_02_NOV, MON_02_NOV));
        }

        @Test
        @Order(3)
        @DisplayName("P3: 1-3-4-6-10-12-14-16-17  ML approved for permanent faculty")
        void pathP3MedicalLeaveApproved() {
            assertEquals("APPROVED: 5 day(s) of ML, balance left 5",
                    service.processRequest(permanent, "ML", MON_02_NOV, MON_02_NOV.plusDays(4)));
        }

        @Test
        @Order(4)
        @DisplayName("P4: 1-3-7-8-10-12-14-16-17  OD approved")
        void pathP4OnDutyLeaveApproved() {
            assertEquals("APPROVED: 3 day(s) of OD, balance left 4",
                    service.processRequest(permanent, "OD", MON_02_NOV, MON_02_NOV.plusDays(2)));
        }

        @Test
        @Order(5)
        @DisplayName("P5: 1-3-7-9-17  unknown leave type")
        void pathP5UnknownLeaveType() {
            assertEquals("REJECTED: unknown leave type EL",
                    service.processRequest(permanent, "EL", MON_02_NOV, MON_02_NOV));
        }

        @Test
        @Order(6)
        @DisplayName("P6: 1-2-10-11-17  period has no leave days (only a Sunday)")
        void pathP6NoLeaveDays() {
            assertEquals("REJECTED: no leave days in the selected period",
                    service.processRequest(permanent, "CL", SUN_01_NOV, SUN_01_NOV));
        }

        @Test
        @Order(7)
        @DisplayName("P7: 1-2-10-12-13-17  CL of 4 days exceeds limit of 3")
        void pathP7LimitExceeded() {
            assertEquals("REJECTED: CL cannot exceed 3 days per request",
                    service.processRequest(permanent, "CL", MON_02_NOV, MON_02_NOV.plusDays(3)));
        }

        @Test
        @Order(8)
        @DisplayName("P8: 1-2-10-12-14-15-17  insufficient CL balance")
        void pathP8InsufficientBalance() {
            Faculty lowBalance = new Faculty("FAC103", "PERMANENT", 1, 10, 7);
            assertEquals("REJECTED: insufficient CL balance",
                    service.processRequest(lowBalance, "CL", MON_02_NOV, MON_02_NOV.plusDays(1)));
            assertEquals(1, lowBalance.getBalance("CL"));
        }

        @Test
        @Order(9)
        @DisplayName("Sat 31-10 to Mon 02-11: Sunday skipped, 2 days approved")
        void sundayInsideRangeIsNotCounted() {
            assertEquals("APPROVED: 2 day(s) of CL, balance left 6",
                    service.processRequest(permanent, "CL", SAT_31_OCT, MON_02_NOV));
        }
    }
}
