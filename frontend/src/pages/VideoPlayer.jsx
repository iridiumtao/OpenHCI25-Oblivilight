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

  const interval = 10000; // 每 10 秒切換一次
  const transitionDuration = 1500; // 轉場動畫 1.5 秒

  const [currentIndex, setCurrentIndex] = useState(0);
  const [showSecondVideo, setShowSecondVideo] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [video1Src, setVideo1Src] = useState("");
  const [video2Src, setVideo2Src] = useState("");

  const video1Ref = useRef(null);
  const video2Ref = useRef(null);

  // 初始化第一個影片
  useEffect(() => {
    if (videos.length > 0) {
      setVideo1Src(videos[0]);
      if (videos.length > 1) {
        setVideo2Src(videos[1]);
      }
    }
  }, []);

  // 自動播放邏輯
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
    const nextVideoRef = showSecondVideo ? video1Ref : video2Ref;

    if (showSecondVideo) {
      setVideo1Src(videos[nextIndex]);
    } else {
      setVideo2Src(videos[nextIndex]);
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
      setShowSecondVideo(!showSecondVideo);
      setIsTransitioning(false);
    }, transitionDuration);
  };

  // 沒影片的 fallback
  if (videos.length === 0) {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading videos...</div>
      </div>
    );
  }

  // 如果只有一部影片
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

  return (
    <div className="fixed inset-0 z-0 bg-black">
      {/* Video 1 */}
      <video
        ref={video1Ref}
        className="w-full h-full object-cover absolute inset-0"
        autoPlay
        muted
        playsInline
        controls={false}
        loop
        src={video1Src}
        style={{
          opacity: showSecondVideo
            ? isTransitioning ? 1 : 0
            : isTransitioning ? 0 : 1,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: showSecondVideo ? 2 : 1
        }}
      />
      {/* Video 2 */}
      <video
        ref={video2Ref}
        className="w-full h-full object-cover absolute inset-0"
        muted
        playsInline
        controls={false}
        loop
        src={video2Src}
        style={{
          opacity: showSecondVideo
            ? isTransitioning ? 0 : 1
            : isTransitioning ? 1 : 0,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: showSecondVideo ? 1 : 2
        }}
      />
      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded z-10">
        Now playing: Video {currentIndex + 1} / {videos.length}
      </div>
    </div>
  );
}

export default VideoPlayer;
