import org.junit.platform.suite.api.SelectClasses;
import org.junit.platform.suite.api.Suite;
import org.junit.platform.suite.api.SuiteDisplayName;

/**
 * JUnit test suite for Expt-9: runs the independent-path tests of both parts together.
 */
@Suite
@SuiteDisplayName("Expt-9 White Box Testing Suite")
@SelectClasses({ TriangleTest.class, EligibilityCriteriaTest.class })
public class WhiteBoxTestSuite {
}
