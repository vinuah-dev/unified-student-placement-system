import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;

/**
 * Basis-path tests for Triangle.classify(): one test per independent path
 * of the control flow graph (V(G) = 11). Node numbers refer to the CFG.
 */
@DisplayName("Part 1 - Triangle.classify() independent paths")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class TriangleTest {

    @Test
    @Order(1)
    @DisplayName("P1: 1-4-17  side a <= 0")
    void path1SideANotPositive() {
        assertEquals("INVALID", Triangle.classify(0, 5, 5));
    }

    @Test
    @Order(2)
    @DisplayName("P2: 1-2-4-17  side b <= 0")
    void path2SideBNotPositive() {
        assertEquals("INVALID", Triangle.classify(4, 0, 3));
    }

    @Test
    @Order(3)
    @DisplayName("P3: 1-2-3-4-17  side c <= 0")
    void path3SideCNotPositive() {
        assertEquals("INVALID", Triangle.classify(4, 3, -2));
    }

    @Test
    @Order(4)
    @DisplayName("P4: 1-2-3-5-8-17  a + b <= c")
    void path4FirstInequalityFails() {
        assertEquals("NOT A TRIANGLE", Triangle.classify(1, 2, 3));
    }

    @Test
    @Order(5)
    @DisplayName("P5: 1-2-3-5-6-8-17  b + c <= a")
    void path5SecondInequalityFails() {
        assertEquals("NOT A TRIANGLE", Triangle.classify(7, 2, 3));
    }

    @Test
    @Order(6)
    @DisplayName("P6: 1-2-3-5-6-7-8-17  a + c <= b")
    void path6ThirdInequalityFails() {
        assertEquals("NOT A TRIANGLE", Triangle.classify(2, 8, 3));
    }

    @Test
    @Order(7)
    @DisplayName("P7: 1-2-3-5-6-7-9-10-11-17  a == b == c")
    void path7Equilateral() {
        assertEquals("EQUILATERAL", Triangle.classify(5, 5, 5));
    }

    @Test
    @Order(8)
    @DisplayName("P8: 1-2-3-5-6-7-9-10-12-17  a == b, b != c")
    void path8IsoscelesAEqualsB() {
        assertEquals("ISOSCELES", Triangle.classify(5, 5, 8));
    }

    @Test
    @Order(9)
    @DisplayName("P9: 1-2-3-5-6-7-9-13-15-17  b == c")
    void path9IsoscelesBEqualsC() {
        assertEquals("ISOSCELES", Triangle.classify(4, 6, 6));
    }

    @Test
    @Order(10)
    @DisplayName("P10: 1-2-3-5-6-7-9-13-14-15-17  a == c")
    void path10IsoscelesAEqualsC() {
        assertEquals("ISOSCELES", Triangle.classify(6, 4, 6));
    }

    @Test
    @Order(11)
    @DisplayName("P11: 1-2-3-5-6-7-9-13-14-16-17  all sides different")
    void path11Scalene() {
        assertEquals("SCALENE", Triangle.classify(3, 4, 5));
    }
}
