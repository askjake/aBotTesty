import { SelectProps } from 'antd';

export interface ReleaseSelectProps extends SelectProps {
  platform?: string;
  onOptionsLoaded?: (firstOptionValue: number) => void;
}
