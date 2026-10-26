/**
 * A student of the Unified Student Placement System (class Student of the Expt-3 class diagram),
 * with the academic data used by the eligibility check.
 */
public class Student {

    private final String rollNo;
    private final String department;
    private final String batch;
    private final double cgpa;
    private final int backlogs;

    public Student(String rollNo, String department, String batch, double cgpa, int backlogs) {
        this.rollNo = rollNo;
        this.department = department;
        this.batch = batch;
        this.cgpa = cgpa;
        this.backlogs = backlogs;
    }

    public String getRollNo() {
        return rollNo;
    }

    public String getDepartment() {
        return department;
    }

    public String getBatch() {
        return batch;
    }

    public double getCgpa() {
        return cgpa;
    }

    public int getBacklogs() {
        return backlogs;
    }
}
