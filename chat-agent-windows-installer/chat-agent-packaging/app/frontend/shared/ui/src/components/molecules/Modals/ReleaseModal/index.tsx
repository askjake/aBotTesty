import { FC, useMemo } from 'react';
import { Modal } from 'antd';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { setShowReleaseModal } from '@shared/ui/store/settings/settings.slice';

import { StyledReleaseModalList } from '@shared/ui/components/molecules/Modals/ReleaseModal/ReleaseModal.styled';

import { ReleaseModalProps } from '@shared/ui/components/molecules/Modals/ReleaseModal/ReleaseModal.props';
import { ReleasesType } from '@shared/ui/types/releases.types';

const ReleaseModal: FC<ReleaseModalProps> = (props) => {
  const dispatch = useAppDispatch();
  const releases = useAppSelector((store) => store.settings.releases);
  const showModal = useAppSelector((store) => store.settings.showReleaseModal);
  const lastRelease = useMemo<ReleasesType | null>(
    () => releases[0] || null,
    [releases],
  );
  return (
    <Modal
      open={showModal}
      title={`${lastRelease?.title || ''}`}
      footer={null}
      onCancel={() => dispatch(setShowReleaseModal(false))}
      centered
      {...props}
    >
      <StyledReleaseModalList>
        {lastRelease?.changes?.map((text, index) => (
          <li key={index}>{text}</li>
        ))}
      </StyledReleaseModalList>
    </Modal>
  );
};

export default ReleaseModal;
