#align centre of wheel with exclamation mark

import viz

viz.go()


txt = viz.addText("!", parent= viz.SCREEN)
txt.setPosition(0.5,.5)
txt.color(viz.WHITE)
txt.visible(1)

viz.window.setFullscreen(viz.ON)