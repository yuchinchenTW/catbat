# Automation Process

1. First run:

```
adb shell am force-stop jp.co.ponos.battlecatstw
adb -s emulator-5554 shell su 0 settings put global auto_time 0
```

2. After **0.5 seconds**, run:

```
for /f %i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-2).ToString('MMddHHmmyyyy.ss')"') do adb -s emulator-5554 shell su 0 date %i
```

3. After **0.5 seconds**, run:

```
adb shell monkey -p jp.co.ponos.battlecatstw -c android.intent.category.LAUNCHER 1
```

4. Wait until **`skip.png`** is detected, then run:

```
adb -s emulator-5554 shell monkey -p app.greyshirts.firewall -c android.intent.category.LAUNCHER 1
```

5. Wait until **`start_green.png`** is detected and click it.

6. Run again:

```
adb shell monkey -p jp.co.ponos.battlecatstw -c android.intent.category.LAUNCHER 1
```

7. When **`skip.png`** is detected, click it.

8. When **`startm.png`** is detected, wait for 1 sec and click it.

9. wait for 0.5sec and then start detect When **`worldm.png`** is detected, click it.only detect for 2 sec if not detected skip this

10.wait for 0.5sec and then start detect When **`worldm2.png`** is detected, click it.only detect for 2 sec if not detected stop entire program

11.wait for 0.5sec and then start detect When **`cross.png`** is detected, wait for 1 sec click it.only detect for 2.5 sec if not detected skip this

12.wait for 0.5sec and then start detect When **`dodo.png`** is detected,wait for 1.5 sec and click 3 time(space 0.5 sec) .if not detected stop entire program

13.wait for 0.5sec and then start detect When **`dodo.png`** is detected,wait for 0.5 sec and click it.if not detected skip this (only wait 1sec)

14. After **1 seconds**, run:

```
adb -s emulator-5554 shell monkey -p app.greyshirts.firewall -c android.intent.category.LAUNCHER 1
```

15. After **1 seconds**, run:

```
adb -s emulator-5554 shell su 0 settings put global auto_time 1
```

16. After **1 second**, run:

```
adb shell monkey -p jp.co.ponos.battlecatstw -c android.intent.category.LAUNCHER 1
```

17. After **0.5 seconds**, run:

```
adb -s emulator-5554 shell monkey -p app.greyshirts.firewall -c android.intent.category.LAUNCHER 1
```

18. Wait until **`start_red.png`** is detected and click it.

19. After **1 second**, run:

```
adb shell monkey -p jp.co.ponos.battlecatstw -c android.intent.category.LAUNCHER 1
```

20
wait for 0.5sec and then start detect When **`gold.png`** is detected, wait for 0.5 sec click it

21
wait for 0.5sec and then start detect When **`result0.png`** is detected, wait for 0.5 sec click it

22
wait for 0.5sec and then start detect When **`result.png`** is detected, wait for 0.5 sec click it

23
wait for 0.5sec and then start detect When **`result1.png`** is detected, wait for 0.5 sec click it

24
wait for 0.5sec and then start detect When **`result2.png`** is detected, wait for 0.5 sec click it(only wait for 1 sec)


25
wait for 0.5sec and then start detect When **`result3.png`** is detected, wait for 0.5 sec click it(only wait for 1 sec)

26
wait for 0.5sec and then start detect When **`map.png`** is detected, wait for 0.5 sec click it
27
wait for 0.5sec and then start detect When **`travel.png`** is detected, wait for 0.5 sec click it
28
wait for 0.5sec and then start detect When **`yes.png`** is detected, wait for 0.5 sec click it

