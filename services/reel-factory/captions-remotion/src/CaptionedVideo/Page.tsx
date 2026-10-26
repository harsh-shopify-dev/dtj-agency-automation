import { makeTransform, scale, translateY } from "@remotion/animation-utils";
import { fitText } from "@remotion/layout-utils";
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../load-font";
import type { DtjPage } from "./index";

// TheBoldFont has Latin only; Gujarati/Hindi captions fall back to a font with those letters (Nirmala UI on Windows,
// Noto Sans Gujarati/Devanagari from fonts-noto-core on the VPS). mahalaxmi-01, 22 Oct 2026.
const fontFamily = `${TheBoldFont}, "Nirmala UI", "Noto Sans Gujarati", "Noto Sans Devanagari", sans-serif`;
const DESIRED_FONT_SIZE = 96;
const SPOKEN = "#FFD400"; // the word being said right now
const KEYWORD = "#FFD400"; // keywords stay yellow after they are said

export const Page: React.FC<{ readonly enterProgress: number; readonly page: DtjPage }> = ({ enterProgress, page }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const timeInMs = (frame / fps) * 1000 + page.startMs;

  const fitted = fitText({ fontFamily, text: page.text, withinWidth: width * 0.84, textTransform: "uppercase" });
  const fontSize = Math.min(DESIRED_FONT_SIZE, fitted.fontSize);
  // marginV is the text bottom's distance from the frame bottom at 1920 px high (Harsh's bottom mark ~548)
  const bottom = (page.marginV / 1920) * height;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom }}>
      <div
        style={{
          fontSize,
          lineHeight: 1.05,
          color: "white",
          WebkitTextStroke: "16px black",
          paintOrder: "stroke",
          textShadow: "0 6px 18px rgba(0,0,0,0.45)",
          fontFamily,
          textTransform: "uppercase",
          textAlign: "center",
          transform: makeTransform([
            scale(interpolate(enterProgress, [0, 1], [0.6, 1])),
            translateY(interpolate(enterProgress, [0, 1], [40, 0])),
          ]),
        }}
      >
        {page.tokens.map((t, i) => {
          const active = t.fromMs <= timeInMs && t.toMs > timeInMs;
          const said = t.toMs <= timeInMs;
          const isKey = page.keywords[i];
          return (
            <span
              key={`${t.fromMs}-${i}`}
              style={{
                display: "inline-block",
                whiteSpace: "pre",
                marginLeft: i === 0 ? 0 : "0.45em",
                color: active ? SPOKEN : said && isKey ? KEYWORD : "white",
                transform: `scale(${active ? 1.06 : 1})`,
              }}
            >
              {t.text.trim()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
