/**
 * Part 1: classifies a triangle from the lengths of its three sides.
 */
public class Triangle {

    public static String classify(int a, int b, int c) {
        if (a <= 0 || b <= 0 || c <= 0) {
            return "INVALID";
        }
        if (a + b <= c || b + c <= a || a + c <= b) {
            return "NOT A TRIANGLE";
        }
        if (a == b) {
            if (b == c) {
                return "EQUILATERAL";
            }
            return "ISOSCELES";
        }
        if (b == c || a == c) {
            return "ISOSCELES";
        }
        return "SCALENE";
    }
}
