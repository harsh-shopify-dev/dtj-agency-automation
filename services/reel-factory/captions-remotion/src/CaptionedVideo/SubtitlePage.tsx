import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { DtjPage } from "./index";
import { Page } from "./Page";

const SubtitlePage: React.FC<{ readonly page: DtjPage }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // springy pop-in: overshoots a little, settles in ~6 frames
  const enter = spring({ frame, fps, config: { damping: 12, stiffness: 220, mass: 0.6 }, durationInFrames: 8 });
  return (
    <AbsoluteFill>
      <Page enterProgress={enter} page={page} />
    </AbsoluteFill>
  );
};

export default SubtitlePage;
