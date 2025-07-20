"use client";

import { useState, useEffect, useRef } from "react";
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

const TRANSITION_DURATION_MS = 1000;

export default function VideoPlayer({ emotion: targetEmotion = "neutral" }) {
  const videoARef = useRef(null);
  const videoBRef = useRef(null);

  const [activeSlot, setActiveSlot] = useState("A");
  const [videoASrc, setVideoASrc] = useState(EMOTION_VIDEOS.neutral);
  const [videoBSrc, setVideoBSrc] = useState(null);

  const emotionInSlotA = useRef("neutral");
  const emotionInSlotB = useRef(null);

  useEffect(() => {
    const activeEmotion = activeSlot === "A" ? emotionInSlotA.current : emotionInSlotB.current;
    
    if (targetEmotion && targetEmotion !== activeEmotion) {
      const inactiveSlot = activeSlot === "A" ? "B" : "A";
      const newSrc = EMOTION_VIDEOS[targetEmotion];

      if (inactiveSlot === "B") {
        emotionInSlotB.current = targetEmotion;
        setVideoBSrc(newSrc);
      } else {
        emotionInSlotA.current = targetEmotion;
        setVideoASrc(newSrc);
      }
      setActiveSlot(inactiveSlot);
    }
  }, [targetEmotion, activeSlot]);

  useEffect(() => {
    const videoRef = activeSlot === 'A' ? videoARef.current : videoBRef.current;
    if (videoRef) {
        videoRef.play().catch(() => {
            // Autoplay might be blocked by the browser.
        });
    }
  }, [activeSlot, videoASrc, videoBSrc]);


  const handleVideoEnded = (slot) => {
    if (slot !== activeSlot) return;

    const endedEmotion = slot === "A" ? emotionInSlotA.current : emotionInSlotB.current;

    if (endedEmotion !== "neutral") {
      const inactiveSlot = activeSlot === "A" ? "B" : "A";
      const newSrc = EMOTION_VIDEOS["neutral"];

      if (inactiveSlot === "B") {
        emotionInSlotB.current = "neutral";
        setVideoBSrc(newSrc);
      } else {
        emotionInSlotA.current = "neutral";
        setVideoASrc(newSrc);
      }
      setActiveSlot(inactiveSlot);
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
          activeSlot === "A" ? "opacity-100" : "opacity-0"
        )}
        style={{ transitionDuration: `${TRANSITION_DURATION_MS}ms` }}
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
          activeSlot === "B" ? "opacity-100" : "opacity-0"
        )}
        style={{ transitionDuration: `${TRANSITION_DURATION_MS}ms` }}
        onEnded={() => handleVideoEnded("B")}
        loop={emotionInSlotB.current === "neutral"}
        autoPlay
        playsInline
        muted
      />
    </div>
  );
} 