# Hi 👋!

This is an UI addon for SublimeLinter.

It highlights the error you jump to when using the Goto commands. Well, okay. 🤹‍♂️🤹‍♀️.

Yeah. Read on. SublimeLinter has a some distraction free capabilities. There is a command
to toggle the squiggles very quickly.  Maybe bind it like so:

```javascript
    // You can toggle all highlights super-fast
    { "keys": ["ctrl+k", "ctrl+k"],
      "command": "sublime_linter_toggle_highlights"
    },
```

There is also a setting "highlights.start_hidden" you can set to `true`.  If true
all views start in distraction/squiggle free mode.

Now, back to this plugin, it will make this experience a bit more awesome.

Namely, it will temporarily jump out of the quiet mode while jumping around the errors
using the goto command or when you have the error panel open. And automatically enter quiet
mode again when you start editing again. (You can control this behavior via the `jump_out_of_quiet` setting.)


