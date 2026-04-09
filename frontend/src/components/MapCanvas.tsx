import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text } from "pixi.js";
import { useCallback } from "react";

// Register PixiJS components with @pixi/react v8 extend API
extend({ Container, Graphics, Text });

export function MapCanvas() {
  const drawGrass = useCallback((graphics: Graphics) => {
    graphics.clear();
    graphics.setFillStyle({ color: 0x2d5a27 });
    graphics.rect(0, 0, 2000, 2000);
    graphics.fill();
  }, []);

  const drawLabel = useCallback((graphics: Graphics) => {
    graphics.clear();
    graphics.setFillStyle({ color: 0x000000, alpha: 0.4 });
    graphics.roundRect(0, 0, 220, 48, 8);
    graphics.fill();
  }, []);

  return (
    <Application
      resizeTo={window}
      background={0x16213e}
    >
      {/* Grass placeholder rectangle */}
      <pixiGraphics draw={drawGrass} />
      {/* Label background */}
      <pixiGraphics
        draw={drawLabel}
        x={20}
        y={20}
      />
    </Application>
  );
}
