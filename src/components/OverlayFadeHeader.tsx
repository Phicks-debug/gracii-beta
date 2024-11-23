interface OverlayFadeHeaderProps {
    overlayHeight: number;
}

export const OverlayFadeHeader = (overlayHeight: OverlayFadeHeaderProps) => {
    return (
        < div className="fixed top-0 left-0 right-0 bottom-0 pointer-events-none z-20" >
            <div
                className="bg-gradient-to-b from-gray-100 via-transparent to-transparent"
                style={{ height: `${overlayHeight}px` }} // Use the overlayHeight state here
            ></div>
        </div >
    )
}