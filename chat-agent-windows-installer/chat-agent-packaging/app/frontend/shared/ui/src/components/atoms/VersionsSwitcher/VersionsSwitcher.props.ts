import { HTMLProps } from 'react';

export interface VersionsSwitcherProps extends HTMLProps<HTMLDivElement> {
  totalVersions: number;
  currentIndex: number;
  updateCurrentVersion: (currentIndex: number) => void;
}
