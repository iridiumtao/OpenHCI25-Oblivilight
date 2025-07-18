import { useEffect, useRef, useState } from "react";

const videos = [
  "/videos/Harmony.mp4",
  "/videos/DreamyPurple.mp4"
];

function VideoPlayer() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const videoRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % videos.length);
    }, 10000); // switch every 10 seconds

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // When video changes, load and play the new one
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {
        // handle autoplay error silently (e.g., if not muted)
      });
    }
  }, [currentIndex]);

  return (
    <div className="fixed inset-0 z-0 bg-black">
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        autoPlay
        muted
        playsInline
        controls={false}
        loop={true}
      >
        <source src={videos[currentIndex]} type="video/mp4" />
        Your browser does not support the video tag.
      </video>
      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded">
        Now playing: Video {currentIndex + 1}
      </div>
    </div>
  );
}

export default VideoPlayer;
