import { FC, useMemo } from 'react';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';

import { useAppSelector } from '@shared/ui/store';

import { StyledVersionsSwitcherContainer } from '@shared/ui/components/atoms/VersionsSwitcher/VersionsSwitcher.styled';

import { VersionsSwitcherProps } from '@shared/ui/components/atoms/VersionsSwitcher/VersionsSwitcher.props';

const VersionsSwitcher: FC<VersionsSwitcherProps> = ({
  totalVersions = 1,
  currentIndex = 0,
  updateCurrentVersion,
}) => {
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const disableLeftBtn = useMemo(
    () => currentIndex <= 0 || aiTyping,
    [currentIndex, aiTyping],
  );
  const disableRightBtn = useMemo(
    () => currentIndex + 1 === totalVersions || aiTyping,
    [currentIndex, totalVersions, aiTyping],
  );

  const onPrev = () => {
    if (disableLeftBtn) return;

    updateCurrentVersion(currentIndex - 1);
  };

  const onNext = () => {
    if (disableRightBtn) return;
    updateCurrentVersion(currentIndex + 1);
  };

  return (
    <StyledVersionsSwitcherContainer
      $disableLeftBtn={disableLeftBtn}
      $disableRightBtn={disableRightBtn}
    >
      <LeftOutlined data-testid='left-button' onClick={() => onPrev()} />
      <span>
        {currentIndex + 1}/{totalVersions}
      </span>
      <RightOutlined data-testid='right-button' onClick={() => onNext()} />
    </StyledVersionsSwitcherContainer>
  );
};

export default VersionsSwitcher;
