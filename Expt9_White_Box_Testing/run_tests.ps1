# Compiles the classes and tests, runs the JUnit suite with JaCoCo coverage, and writes the reports.
# Usage (from this folder):  powershell -ExecutionPolicy Bypass -File run_tests.ps1
# Set JAVA_HOME to a JDK 17+ first if 'java' is not on PATH.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$java = "java"; $javac = "javac"
if ($env:JAVA_HOME) { $java = "$env:JAVA_HOME\bin\java.exe"; $javac = "$env:JAVA_HOME\bin\javac.exe" }

$junit  = "lib\junit-platform-console-standalone-1.11.4.jar"
$agent  = "lib\jacoco-0.8.12\lib\jacocoagent.jar"
$cli    = "lib\jacoco-0.8.12\lib\jacococli.jar"

Remove-Item -Recurse -Force out, reports -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force out\classes, out\test-classes, reports | Out-Null

& $javac -d out\classes src\*.java
& $javac -d out\test-classes -cp "out\classes;$junit" test\*.java

# Run only the suite class, so the tests are executed through WhiteBoxTestSuite.
& $java "-javaagent:$agent=destfile=out\jacoco.exec" -jar $junit execute `
    --class-path "out\classes;out\test-classes" `
    --select-class WhiteBoxTestSuite `
    --details=tree --disable-banner --disable-ansi-colors `
    --reports-dir reports\junit | Tee-Object -FilePath reports\junit-console-output.txt

& $java -jar $cli report out\jacoco.exec --classfiles out\classes --sourcefiles src `
    --html reports\coverage --csv reports\coverage.csv --name "Expt-9 White Box Testing"
