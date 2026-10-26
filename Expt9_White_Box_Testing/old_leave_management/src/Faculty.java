import java.util.HashMap;
import java.util.Map;

/**
 * A faculty member of the Online Leave Management System with a category
 * (PERMANENT or CONTRACT) and an available balance for each leave type (CL, ML, OD).
 */
public class Faculty {

    private final String id;
    private final String category;
    private final Map<String, Integer> balance = new HashMap<>();

    public Faculty(String id, String category, int clBalance, int mlBalance, int odBalance) {
        this.id = id;
        this.category = category;
        balance.put("CL", clBalance);
        balance.put("ML", mlBalance);
        balance.put("OD", odBalance);
    }

    public String getId() {
        return id;
    }

    public boolean isContract() {
        return "CONTRACT".equals(category);
    }

    public int getBalance(String leaveType) {
        return balance.get(leaveType);
    }

    public void deduct(String leaveType, int days) {
        balance.put(leaveType, balance.get(leaveType) - days);
    }
}
