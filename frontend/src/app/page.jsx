"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { useProjectorState } from "../hooks/useProjectorState";

// Dynamically import VideoPlayer to avoid SSR issues with video elements
const VideoPlayer = dynamic(() => import("../components/VideoPlayer"), {
  ssr: false,
});

function StatusIndicator({ isConnected }) {
  return (
    <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1.5 rounded-lg text-sm z-30">
      WebSocket:{" "}
      <span className={isConnected ? "text-green-400" : "text-red-400"}>
        {isConnected ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}

function ModeOverlay({ mode }) {
  const [isSleepVisible, setIsSleepVisible] = useState(false);

  // States for FORGET effect
  const [isForgetOverlayVisible, setIsForgetOverlayVisible] = useState(false);

  // States for REWIND effect
  const [isRewindBlackoutVisible, setIsRewindBlackoutVisible] = useState(false);
  const [isRewindTextVisible, setIsRewindTextVisible] = useState(false);

  useEffect(() => {
    // SLEEP mode simple visibility
    setIsSleepVisible(mode === "SLEEP");

    // FORGET mode animation
    if (mode === "FORGET") {
      setIsForgetOverlayVisible(true);
    } else {
      setIsForgetOverlayVisible(false);
    }

    // REWIND mode animation
    if (mode === "REWIND") {
      setIsRewindBlackoutVisible(true);
      const textTimer = setTimeout(() => setIsRewindTextVisible(true), 700);
      return () => clearTimeout(textTimer);
    } else {
      setIsRewindTextVisible(false);
      const blackoutTimer = setTimeout(() => setIsRewindBlackoutVisible(false), 300); // Let text fade out first
      return () => clearTimeout(blackoutTimer);
    }
  }, [mode]);

  return (
    <>
      {/* Sleep Blackout (z-10) */}
      <div
        className={clsx(
          "absolute inset-0 z-10 bg-black transition-opacity duration-1000",
          isSleepVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      />

      {/* Forget Overlay (z-20) */}
      <div
        className={clsx(
          "absolute inset-0 z-20 bg-black transition-opacity duration-500",
          isForgetOverlayVisible ? "opacity-75" : "opacity-0 pointer-events-none"
        )}
      />

      {/* Rewind Blackout (z-30) */}
      <div
        className={clsx(
          "absolute inset-0 z-30 bg-black transition-opacity duration-300",
          isRewindBlackoutVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      />

      {/* Rewind Text (z-40) */}
      <div
        className={clsx(
          "absolute inset-0 z-40 flex items-center justify-center transition-opacity duration-300",
          isRewindTextVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      >
        <div className="text-white text-6xl font-bold animate-pulse">
          REWIND
        </div>
      </div>
    </>
  );
}

export default function Home() {
  const { emotion, mode, isConnected } = useProjectorState();

  const emotionToPlay =
    mode === "IDLE" || mode === "REWIND" ? emotion : "neutral";

  return (
    <main className="relative w-screen h-screen bg-black overflow-hidden">
      <StatusIndicator isConnected={isConnected} />
      <VideoPlayer emotion={emotionToPlay} />
      <ModeOverlay mode={mode} />
    </main>
  );
} 