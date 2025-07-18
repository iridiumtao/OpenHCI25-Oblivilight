import { useEffect, useRef, useState } from "react";

function VideoPlayer({ index }) {
  const videos = [
    "videos/neutral.mp4",
    "videos/happy.mp4",
    "videos/sad.mp4",
    "videos/warm.mp4",
    "videos/optimistic.mp4",
    "videos/anxious.mp4",
    "videos/peaceful.mp4",
    "videos/depressed.mp4",
    "videos/lonely.mp4",
    "videos/angry.mp4"
  ];

  const interval = 3000; // 每 10 秒切換
  const transitionDuration = 1500;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [nextIndex, setNextIndex] = useState(null);
  const [isSecondActive, setIsSecondActive] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const [videoA, setVideoA] = useState(videos[0]);
  const [videoB, setVideoB] = useState(""); // 初始不載入

  const videoARef = useRef(null);
  const videoBRef = useRef(null);

  // 監聽 props.index 變化，若合法且不是 currentIndex，就更新 nextIndex
  useEffect(() => {
    if (
      typeof index === "number" &&
      index >= 0 &&
      index < videos.length &&
      index !== currentIndex
    ) {
      setNextIndex(index);
    }
  }, [index]);

  // 每 10 秒觸發檢查是否需要切換影片
  useEffect(() => {
    const timer = setInterval(() => {
      const hasNewIndex =
        typeof nextIndex === "number" &&
        nextIndex >= 0 &&
        nextIndex < videos.length &&
        nextIndex !== currentIndex;

      const targetIndex = hasNewIndex
        ? nextIndex
        : currentIndex === 0
        ? 0
        : 0; // fallback 為 video[0]

      // 如果 fallback 也是目前的影片，不做任何事
      if (targetIndex === currentIndex) return;

      startTransition(targetIndex);
    }, interval);

    return () => clearInterval(timer);
  }, [nextIndex, currentIndex]);

  // 切換影片
  const startTransition = (targetIndex) => {
    if (isTransitioning || targetIndex === currentIndex) return;

    const nextSrc = videos[targetIndex];
    const nextVideoRef = isSecondActive ? videoARef : videoBRef;

    if (isSecondActive) {
      setVideoA(nextSrc);
      console.log("切換到影片 A:", nextSrc, targetIndex + 1);
    } else {
      setVideoB(nextSrc);
      console.log("切換到影片 B:", nextSrc, targetIndex + 1);
    }

    setIsTransitioning(true);

    setTimeout(() => {
      if (nextVideoRef.current) {
        nextVideoRef.current.play().catch(() => {
          // silent autoplay error
        });
      }
    }, 100);

    setTimeout(() => {
      setCurrentIndex(targetIndex);
      setIsSecondActive(!isSecondActive);
      setIsTransitioning(false);
      setNextIndex(null); // 清除已使用的待播影片
    }, transitionDuration);
  };

  // 決定當前影片 src
  const currentVideoSrc = isSecondActive ? videoB : videoA;
  const nextVideoSrc = isSecondActive ? videoA : videoB;

  // fallback 處理
  if (videos.length === 0) {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading videos...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-0 bg-black">
      {/* Video A */}
      <video
        ref={videoARef}
        className="w-full h-full object-cover absolute inset-0"
        autoPlay
        muted
        playsInline
        controls={false}
        loop
        src={videoA}
        style={{
          opacity: isSecondActive
            ? isTransitioning
              ? 1
              : 0
            : isTransitioning
              ? 0
              : 1,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: isSecondActive ? 2 : 1
        }}
      />

      {/* Video B */}
      <video
        ref={videoBRef}
        className="w-full h-full object-cover absolute inset-0"
        muted
        playsInline
        controls={false}
        loop
        src={videoB}
        style={{
          opacity: isSecondActive
            ? isTransitioning
              ? 0
              : 1
            : isTransitioning
              ? 1
              : 0,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: isSecondActive ? 1 : 2
        }}
      />

      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded z-10">
        Now playing: Video {currentIndex + 1} / {videos.length}
      </div>
    </div>
  );
}

export default VideoPlayer;
