import { FC, useMemo } from 'react';
import { Switch } from 'antd';
import { MoonOutlined, SunOutlined } from '@ant-design/icons';

import { toggleThemeMode } from '@shared/ui/store/settings/settings.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';

import { ThemeSwitcherProps } from '@shared/ui/components/molecules/Switchers/ThemeSwitcher/ThemeSwitcher.props';

const ThemeSwitcher: FC<ThemeSwitcherProps> = ({
  className = '',
  ...props
}) => {
  const dispatch = useAppDispatch();
  const themeMode = useAppSelector((store) => store.settings.themeMode);
  const checkedTheme = useMemo(() => themeMode === 'dark', [themeMode]);
  return (
    <Switch
      className={`theme-switcher ${className}`}
      checked={checkedTheme}
      checkedChildren={<MoonOutlined />}
      unCheckedChildren={<SunOutlined />}
      onChange={() => dispatch(toggleThemeMode())}
      {...props}
    />
  );
};

export default ThemeSwitcher;
