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

  let offsetAccumulator = 0;

  return (
    <View style={{ width: size, height: size }}>
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
          const gap = circumference - dash;
          const rotation = (offsetAccumulator / total) * 360 - 90;
          offsetAccumulator += slice.value;

          return (
            <Circle
              key={idx}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={slice.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${dash} ${gap}`}
              strokeLinecap="butt"
              fill="none"
              rotation={rotation}
              origin={`${size / 2}, ${size / 2}`}
            />
          );
        })}
      </Svg>
    </View>
  );
}
