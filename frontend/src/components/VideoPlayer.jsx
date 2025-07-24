"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import clsx from "clsx";

const EMOTION_VIDEOS = {
  neutral: "videos/neutral.mp4",
  happy: "videos/happy.mp4",
  sad: "videos/sad.mp4",
  warm: "videos/warm.mp4",
  optimistic: "videos/optimistic.mp4",
  anxious: "videos/anxious.mp4",
  peaceful: "videos/peaceful.mp4",
  depressed: "videos/depressed.mp4",
  lonely: "videos/lonely.mp4",
  angry: "videos/angry.mp4",
};

const TRANSITION_DURATION_MS = 2000;
const COOLDOWN_MS = 3000;

export default function VideoPlayer({ emotion: targetEmotion = "neutral" }) {
  const videoARef = useRef(null);
  const videoBRef = useRef(null);
  
  const [activeSlot, setActiveSlot] = useState("A");
  const [videoASrc, setVideoASrc] = useState(EMOTION_VIDEOS.neutral);
  const [videoBSrc, setVideoBSrc] = useState(null);
  const [isOnCooldown, setIsOnCooldown] = useState(false);

  const emotionInSlotA = useRef("neutral");
  const emotionInSlotB = useRef(null);
  
  const transitionToVideo = useCallback((newEmotion, newSlot) => {
    if (isOnCooldown) return;
    
    const newSrc = EMOTION_VIDEOS[newEmotion];
    
    if (newSlot === "B") {
      emotionInSlotB.current = newEmotion;
      setVideoBSrc(newSrc);
    } else {
      emotionInSlotA.current = newEmotion;
      setVideoASrc(newSrc);
    }
  }, [isOnCooldown]);

  useEffect(() => {
    const activeEmotion = activeSlot === "A" ? emotionInSlotA.current : emotionInSlotB.current;
    if (targetEmotion && targetEmotion !== activeEmotion) {
      const inactiveSlot = activeSlot === "A" ? "B" : "A";
      transitionToVideo(targetEmotion, inactiveSlot);
    }
  }, [targetEmotion, activeSlot, transitionToVideo]);

  const handleCanPlayThrough = (slotToActivate) => {
    if (activeSlot === slotToActivate) return;

    setActiveSlot(slotToActivate);
    setIsOnCooldown(true);
    setTimeout(() => {
      setIsOnCooldown(false);
    }, COOLDOWN_MS);
  };

  useEffect(() => {
    const videoA = videoARef.current;
    const videoB = videoBRef.current;

    if (activeSlot === 'A' && videoA) {
      videoA.play().catch(() => {});
      if (videoB) videoB.pause();
    } else if (activeSlot === 'B' && videoB) {
      videoB.play().catch(() => {});
      if (videoA) videoA.pause();
    }
  }, [activeSlot, videoASrc, videoBSrc]);

  const handleVideoEnded = (slot) => {
    if (slot !== activeSlot || isOnCooldown) return;

    const endedEmotion = slot === "A" ? emotionInSlotA.current : emotionInSlotB.current;
    if (endedEmotion !== "neutral") {
      const inactiveSlot = activeSlot === "A" ? "B" : "A";
      transitionToVideo("neutral", inactiveSlot);
    }
  };
  
  return (
    <div className="absolute inset-0 w-full h-full bg-black">
      <video
        ref={videoARef}
        key={videoASrc}
        src={videoASrc}
        className={clsx(
          "absolute inset-0 w-full h-full object-cover transition-opacity",
          {
            "opacity-100": activeSlot === "A",
            "opacity-0": activeSlot !== "A",
          }
        )}
        style={{ transitionDuration: `${TRANSITION_DURATION_MS}ms` }}
        onCanPlayThrough={() => handleCanPlayThrough('A')}
        onEnded={() => handleVideoEnded("A")}
        loop={emotionInSlotA.current === "neutral"}
        autoPlay
        playsInline
        muted
      />
      <video
        ref={videoBRef}
        key={videoBSrc}
        src={videoBSrc}
        className={clsx(
          "absolute inset-0 w-full h-full object-cover transition-opacity",
          {
            "opacity-100": activeSlot === "B",
            "opacity-0": activeSlot !== "B",
          }
        )}
        style={{ transitionDuration: `${TRANSITION_DURATION_MS}ms` }}
        onCanPlayThrough={() => handleCanPlayThrough('B')}
        onEnded={() => handleVideoEnded("B")}
        loop={emotionInSlotB.current === "neutral"}
        autoPlay
        playsInline
        muted
      />
    </div>
  );
}