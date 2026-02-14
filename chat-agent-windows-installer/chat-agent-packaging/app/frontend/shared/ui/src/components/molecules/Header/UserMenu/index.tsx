import { FC, useMemo, useState } from 'react';
import { Dropdown, MenuProps } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import dynamic from 'next/dynamic';

const ReleasesNotesDrawer = dynamic(
  () => import('@shared/ui/components/molecules/Drawers/ReleasesNotesDrawer'),
  {
    ssr: false,
  },
);

import { UserMenuProps } from '@shared/ui/components/molecules/Header/UserMenu/UserMenu.props';

const UserMenu: FC<UserMenuProps> = ({
  children,
  className = '',
  ...props
}) => {
  const [showReleases, setShowReleases] = useState(false);
  const items: MenuProps['items'] = useMemo(
    () => [
      {
        label: `What's new?`,
        key: '0',
        icon: <QuestionCircleOutlined />,
        onClick: () => {
          setShowReleases(true);
        },
      },
    ],
    [],
  );
  return (
    <>
      <Dropdown
        className={`user-menu ${className}`}
        menu={{ items }}
        trigger={['click']}
        {...props}
      >
        {children}
      </Dropdown>
      <ReleasesNotesDrawer
        open={showReleases}
        onClose={() => setShowReleases(false)}
      />
    </>
  );
};

export default UserMenu;
