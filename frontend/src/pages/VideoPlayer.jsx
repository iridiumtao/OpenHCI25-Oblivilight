import { useEffect, useRef, useState } from "react";

function VideoPlayer() {
  const videos = [
    "videos/neutral_.mp4",
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

  const interval = 10000;
  const transitionDuration = 1500;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isSecondActive, setIsSecondActive] = useState(false); // 對應原本 showSecondVideo
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [videoA, setVideoA] = useState("");
  const [videoB, setVideoB] = useState("");

  const videoARef = useRef(null);
  const videoBRef = useRef(null);

  // 初始化第一與第二影片
  useEffect(() => {
    if (videos.length > 0) {
      setVideoA(videos[0]);
      if (videos.length > 1) {
        setVideoB(videos[1]);
      }
    }
  }, []);

  // 自動切換邏輯
  useEffect(() => {
    if (videos.length <= 1) return;

    const intervalId = setInterval(() => {
      startTransition();
    }, interval);

    return () => clearInterval(intervalId);
  }, [currentIndex]);

  const startTransition = () => {
    if (videos.length <= 1 || isTransitioning) return;

    const nextIndex = (currentIndex + 1) % videos.length;
    const nextVideoRef = isSecondActive ? videoARef : videoBRef;

    // 預載下一個影片
    if (isSecondActive) {
      setVideoA(videos[nextIndex]);
    } else {
      setVideoB(videos[nextIndex]);
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
      setCurrentIndex(nextIndex);
      setIsSecondActive(!isSecondActive);
      setIsTransitioning(false);
    }, transitionDuration);
  };

  if (videos.length === 0) {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading videos...</div>
      </div>
    );
  }

  if (videos.length === 1) {
    return (
      <div className="fixed inset-0 z-0 bg-black">
        <video
          className="w-full h-full object-cover"
          autoPlay
          muted
          playsInline
          controls={false}
          loop
          src={videos[0]}
        />
        <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded">
          Now playing: {videos[0]}
        </div>
      </div>
    );
  }

  const currentVideoSrc = isSecondActive ? videoB : videoA;
  const nextVideoSrc = isSecondActive ? videoA : videoB;

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
            ? isTransitioning ? 1 : 0
            : isTransitioning ? 0 : 1,
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
            ? isTransitioning ? 0 : 1
            : isTransitioning ? 1 : 0,
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
