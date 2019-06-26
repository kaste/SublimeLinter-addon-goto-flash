# Hi :wave:!

This is an UI addon for SublimeLinter.

It highlights the error you jump to when using the Goto commands. Yep, it's more on the fancy side :man_juggling::woman_juggling:.

The plugin works very well with SublimeLinter's 'quiet' mode. (Reminder: A 'quiet' view doesn't show underlines (etc.) in the code, it still draws gutter marks, and the panel is also fully functional.) 

By default it will temporarily jump out of the quiet mode while jumping around the errors using the goto command, and enter quiet mode again when you start editing again. (You can control this behavior via the `jump_out_of_quiet`setting.)

Optionally, using the `only_if_quiet` setting, you can turn off the flashing if the view is *not* quiet.



