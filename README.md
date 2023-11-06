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

And there is also a setting "highlights.start_hidden" you can use.  Refer to the
original documentation for the possible values here.

Anyhow, back to this plugin, it will make this experience a bit more awesome.

Namely, it will temporarily jump out of the quiet mode while jumping around the errors
using the goto command or when you have the error panel open. And automatically enter quiet
mode again when you start editing again. (You can control this behavior via the `jump_out_of_quiet` setting.)


### Example

You configure to display phantoms for some errors in SublimeLinter.

```
    "styles": [
        {
            ...
            "phantom": "{msg}"
        }
    ],
```

You also set

```
  "highlights.start_hidden": ["phantoms"],
```

in the main SublimeLinter settings.

With that applied, you already don't see any phantoms while you type.  But you can
toggle them quickly using `ctrl+k ctrl+k`.  You just have squiggles while typing
and get the error detail per key-stroke.  🫣

Now again, this addon here comes into play.  If you set `jump_out_of_quiet`, it
will temporarily toggle the phantoms when you jump around the errors using e.g.
`ctrl+k ctrl+n` and hide them again for you.

Anyhow, the idea is to configure phantoms and squiggles but to hide some or all
of them while typing.  😏
