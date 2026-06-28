import { Fragment } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Line, Rect } from 'react-native-svg';

import { Colors } from '@/constants/theme';
import { Candle } from '@/services/binance';

interface CandlestickChartProps {
  candles: Candle[];
  width: number;
  height?: number;
}

export function CandlestickChart({ candles, width, height = 220 }: CandlestickChartProps) {
  if (candles.length === 0) {
    return (
      <View style={[styles.empty, { width, height }]}>
        <Text style={styles.emptyText}>Loading chart…</Text>
      </View>
    );
  }

  const highs = candles.map((c) => c.high);
  const lows = candles.map((c) => c.low);
  const maxRaw = Math.max(...highs);
  const minRaw = Math.min(...lows);
  const padding = (maxRaw - minRaw) * 0.08 || maxRaw * 0.01 || 1;
  const max = maxRaw + padding;
  const min = minRaw - padding;
  const range = max - min || 1;

  const candleWidth = width / candles.length;
  const bodyWidth = Math.max(candleWidth * 0.6, 1);

  const y = (value: number) => height - ((value - min) / range) * height;

  return (
    <Svg width={width} height={height}>
      {candles.map((c, i) => {
        const bullish = c.close >= c.open;
        const color = bullish ? Colors.gain : Colors.loss;
        const cx = i * candleWidth + candleWidth / 2;
        const bodyTop = y(Math.max(c.open, c.close));
        const bodyBottom = y(Math.min(c.open, c.close));

        return (
          <Fragment key={c.time}>
            <Line x1={cx} y1={y(c.high)} x2={cx} y2={y(c.low)} stroke={color} strokeWidth={1} />
            <Rect
              x={cx - bodyWidth / 2}
              y={bodyTop}
              width={bodyWidth}
              height={Math.max(bodyBottom - bodyTop, 1)}
              fill={color}
            />
          </Fragment>
        );
      })}
    </Svg>
  );
}

const styles = StyleSheet.create({
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    fontFamily: 'Inter_500Medium',
    fontSize: 13,
    color: Colors.muted,
  },
});
