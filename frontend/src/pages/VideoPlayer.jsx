import { useEffect, useRef, useState } from "react";

function VideoPlayer({ videos = ["videos/video1.mp4", "videos/video2.mp4"], interval = 10000, transitionDuration = 1500 }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showSecondVideo, setShowSecondVideo] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [video1Src, setVideo1Src] = useState("");
  const [video2Src, setVideo2Src] = useState("");
  
  const video1Ref = useRef(null);
  const video2Ref = useRef(null);

  // 初始化第一個影片
  useEffect(() => {
    if (videos && videos.length > 0) {
      setVideo1Src(videos[0]);
      if (videos.length > 1) {
        setVideo2Src(videos[1]);
      }
    }
  }, [videos]);

  // 自動播放邏輯
  useEffect(() => {
    if (!videos || videos.length <= 1) return;
    
    const intervalId = setInterval(() => {
      startTransition();
    }, interval);

    return () => clearInterval(intervalId);
  }, [videos, interval, currentIndex]);

  const startTransition = () => {
    if (!videos || videos.length <= 1 || isTransitioning) return;
    
    const nextIndex = (currentIndex + 1) % videos.length;
    const nextVideoRef = showSecondVideo ? video1Ref : video2Ref;
    
    // 預載下一個影片到即將顯示的 video 元素
    if (showSecondVideo) {
      // 如果現在顯示 video2，下一個要顯示 video1
      setVideo1Src(videos[nextIndex]);
    } else {
      // 如果現在顯示 video1，下一個要顯示 video2
      setVideo2Src(videos[nextIndex]);
    }
    
    setIsTransitioning(true);
    
    // 等待影片載入並開始轉場
    setTimeout(() => {
      if (nextVideoRef.current) {
        nextVideoRef.current.play().catch(() => {
          // handle autoplay error silently
        });
      }
    }, 100);
    
    // 開始轉場
    setTimeout(() => {
      setCurrentIndex(nextIndex);
      setShowSecondVideo(!showSecondVideo);
      setIsTransitioning(false);
    }, transitionDuration);
  };

  // 如果沒有影片資料
  if (!videos || videos.length === 0) {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading videos...</div>
      </div>
    );
  }

  // 如果只有一個影片
  if (videos.length === 1) {
    return (
      <div className="fixed inset-0 z-0 bg-black">
        <video
          className="w-full h-full object-cover"
          autoPlay
          muted
          playsInline
          controls={false}
          loop={true}
          src={videos[0]}
        >
          Your browser does not support the video tag.
        </video>
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
        loop={true}
        src={video1Src}
        style={{
          opacity: showSecondVideo ? 
            (isTransitioning ? 1 : 0) : 
            (isTransitioning ? 0 : 1),
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: showSecondVideo ? 2 : 1
        }}
      >
        Your browser does not support the video tag.
      </video>
      
      {/* Video 2 */}
      <video
        ref={video2Ref}
        className="w-full h-full object-cover absolute inset-0"
        muted
        playsInline
        controls={false}
        loop={true}
        src={video2Src}
        style={{
          opacity: showSecondVideo ? 
            (isTransitioning ? 0 : 1) : 
            (isTransitioning ? 1 : 0),
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: showSecondVideo ? 1 : 2
        }}
      >
        Your browser does not support the video tag.
      </video>
      
      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded z-10">
        Now playing: Video {currentIndex + 1} / {videos.length}
      </div>
    </div>
  );
}

export default VideoPlayer;
