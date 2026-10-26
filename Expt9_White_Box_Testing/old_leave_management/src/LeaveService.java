import java.time.DayOfWeek;
import java.time.LocalDate;

/**
 * Part 2: Leave Service of the Online Leave Management System.
 * Counts the leave days of a request, checks it against the leave policy,
 * approves or rejects it, and updates the faculty member's leave balance.
 */
public class LeaveService {

    public static final int CL_LIMIT = 3;
    public static final int ML_LIMIT = 15;
    public static final int OD_LIMIT = 10;

    /** Number of leave days from 'from' to 'to' (both inclusive); Sundays are not counted. */
    public int countLeaveDays(LocalDate from, LocalDate to) {
        int days = 0;
        LocalDate day = from;
        while (!day.isAfter(to)) {
            if (day.getDayOfWeek() != DayOfWeek.SUNDAY) {
                days++;
            }
            day = day.plusDays(1);
        }
        return days;
    }

    /** Applies the leave policy to a request and returns the decision. */
    public String processRequest(Faculty faculty, String leaveType, LocalDate from, LocalDate to) {
        int limit;
        if (leaveType.equals("CL")) {
            limit = CL_LIMIT;
        } else if (leaveType.equals("ML")) {
            if (faculty.isContract()) {
                return "REJECTED: contract faculty are not eligible for ML";
            }
            limit = ML_LIMIT;
        } else if (leaveType.equals("OD")) {
            limit = OD_LIMIT;
        } else {
            return "REJECTED: unknown leave type " + leaveType;
        }

        int days = countLeaveDays(from, to);
        if (days == 0) {
            return "REJECTED: no leave days in the selected period";
        }
        if (days > limit) {
            return "REJECTED: " + leaveType + " cannot exceed " + limit + " days per request";
        }
        if (days > faculty.getBalance(leaveType)) {
            return "REJECTED: insufficient " + leaveType + " balance";
        }
        faculty.deduct(leaveType, days);
        int left = faculty.getBalance(leaveType);
        return "APPROVED: " + days + " day(s) of " + leaveType + ", balance left " + left;
    }
}
