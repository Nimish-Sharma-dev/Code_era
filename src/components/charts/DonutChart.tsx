import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

export interface DonutSlice {
  value: number;
  color: string;
}

interface DonutChartProps {
  slices: DonutSlice[];
  size?: number;
  strokeWidth?: number;
}

export function DonutChart({ slices, size = 160, strokeWidth = 22 }: DonutChartProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const total = slices.reduce((s, sl) => s + sl.value, 0) || 1;

  let cumulativeFraction = 0;

  return (
    // Rotate via a plain RN style transform (not react-native-svg's per-element
    // rotation/origin props, which threw on web) so the first slice starts at
    // 12 o'clock instead of the SVG circle's default 3 o'clock start point.
    <View style={{ width: size, height: size, transform: [{ rotate: '-90deg' }] }}>
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#2A2D3A"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {slices.map((slice, idx) => {
          const fraction = slice.value / total;
          const dash = fraction * circumference;
          const dashOffset = circumference * (1 - cumulativeFraction);
          cumulativeFraction += fraction;

          return (
            <Circle
              key={idx}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={slice.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={dashOffset}
              strokeLinecap="butt"
              fill="none"
            />
          );
        })}
      </Svg>
    </View>
  );
}
