import { getVideoMetadata } from "@remotion/media-utils";
import { useCallback, useEffect, useState } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  cancelRender,
  OffthreadVideo,
  Sequence,
  staticFile,
  useDelayRender,
  useVideoConfig,
} from "remotion";
import { z } from "zod";
import { loadFont } from "../load-font";
import SubtitlePage from "./SubtitlePage";

// One caption page, exported by reel_factory/edit.py (script spelling, ends at each cut, skipped on product-name shots).
export type DtjPage = {
  text: string;
  startMs: number;
  durationMs: number;
  marginV: number; // distance of the text bottom from the frame bottom, in px at 1920 high
  keywords: boolean[];
  tokens: { text: string; fromMs: number; toMs: number }[];
};

export const captionedVideoSchema = z.object({
  src: z.string(),
});

// A bare file name is a file in public/; a URL or absolute path is used as it is.
const resolve = (src: string) => (/^(https?:|\/)/.test(src) ? src : staticFile(src));

export const calculateCaptionedVideoMetadata: CalculateMetadataFunction<
  z.infer<typeof captionedVideoSchema>
> = async ({ props }) => {
  const fps = 30;
  const metadata = await getVideoMetadata(resolve(props.src));
  return { fps, durationInFrames: Math.floor(metadata.durationInSeconds * fps) };
};

export const CaptionedVideo: React.FC<{ src: string }> = ({ src: file }) => {
  const src = resolve(file);
  const [pages, setPages] = useState<DtjPage[]>([]);
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());
  const { fps } = useVideoConfig();
  const pagesFile = src.replace(/\.(mp4|mov|mkv|webm)$/, ".pages.json");

  const load = useCallback(async () => {
    try {
      await loadFont();
      const res = await fetch(pagesFile);
      setPages(res.ok ? ((await res.json()) as DtjPage[]) : []);
      continueRender(handle);
    } catch (e) {
      cancelRender(e);
    }
  }, [continueRender, handle, pagesFile]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill>
        <OffthreadVideo style={{ objectFit: "cover" }} src={src} />
      </AbsoluteFill>
      {pages.map((page, index) => {
        const from = Math.round((page.startMs / 1000) * fps);
        const dur = Math.max(1, Math.round((page.durationMs / 1000) * fps));
        return (
          <Sequence key={index} from={from} durationInFrames={dur}>
            <SubtitlePage page={page} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
